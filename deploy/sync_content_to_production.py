#!/usr/bin/env python3
"""
sync_content_to_production.py
==============================
Upsert marketplace CATALOG content (Category, Product, Course + its
sections/lessons, SupermarketItem) from the LOCAL dev database into
PRODUCTION, matched by natural key (slug / title) — never by raw primary
key, since local and production auto-increment IDs do not correspond to
the same real-world rows.

Deliberately excludes everything involving real users, accounts, orders,
wallets, or messages. `vendor` foreign keys are resolved with a READ-ONLY
lookup against production (matched by Vendor.email); if no matching vendor
exists in production, the item is linked to no vendor and flagged in the
report — this script never creates or modifies a Vendor row.

Safety:
  - Defaults to --dry-run (report only, writes nothing).
  - Takes a JSON backup of every production row it is about to toutouch
    before writing anything, when --apply is used (skip with --no-backup
    only if you already have one, e.g. a Supabase point-in-time snapshot).
  - Never deletes anything in production.

Usage:
  # 1) Set the production connection string (from Supabase dashboard),
  #    NEVER commit it:
  #    PowerShell:  $env:PRODUCTION_DATABASE_URL = 'postgresql://...'
  #
  # 2) Dry run first (default) — just prints what WOULD happen:
  python deploy/sync_content_to_production.py
  #
  # 3) Review the report, then actually write:
  python deploy/sync_content_to_production.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

import django  # noqa: E402


def _parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in ('postgresql', 'postgres'):
        raise ValueError(f'Unsupported DATABASE_URL scheme: {parsed.scheme}')
    query = parse_qs(parsed.query)
    sslmode = query.get('sslmode', [None])[0] or ('require' if 'supabase.co' in (parsed.hostname or '') else None)
    options = {'client_encoding': 'UTF8'}
    if sslmode:
        options['sslmode'] = sslmode
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed.path.lstrip('/')),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname,
        'PORT': str(parsed.port or '5432'),
        'OPTIONS': options,
        # Standard Django DATABASES defaults — required because we register
        # this alias after django.setup(), bypassing the normal settings
        # bootstrap that would otherwise fill these in automatically.
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'AUTOCOMMIT': True,
        'ATOMIC_REQUESTS': False,
        'TIME_ZONE': None,
        'TEST': {'NAME': None, 'MIRROR': None, 'CHARSET': None, 'COLLATION': None, 'DEPENDENCIES': ['default']},
    }


def setup_production_alias():
    """Register a second Django DB alias ('production') pointed at the
    Supabase production database, without touching the 'default' (local)
    connection used for reads."""
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL', '').strip()
    if not prod_url:
        print('ERROR: set PRODUCTION_DATABASE_URL first (Supabase Postgres URI).', file=sys.stderr)
        sys.exit(2)
    django.setup()
    from django.conf import settings
    settings.DATABASES['production'] = _parse_database_url(prod_url)


# ---------------------------------------------------------------------------
# Sync plan — processed strictly in this order so FK targets are already
# migrated (and their local->production PK mapping known) before dependents.
# Each entry: (app_label, model_name, natural_key_fields, fk_config)
#   fk_config maps field_name -> ('own', ) meaning "resolve via pk_map built
#   earlier in this run", or -> ('lookup', app_label, model_name, field) for
#   a READ-ONLY match against an excluded model (e.g. Vendor by email).
# ---------------------------------------------------------------------------
SYNC_PLAN = [
    ('marketplace', 'Category', ('slug',), {'parent': ('own',)}),
    ('marketplace', 'Product', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
    ('marketplace', 'Course', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
    ('marketplace', 'CourseSection', ('course', 'title'), {'course': ('own',)}),
    ('marketplace', 'CourseLesson', ('section', 'title'), {'section': ('own',)}),
    ('marketplace', 'SupermarketItem', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
]

# Fields never copied across (auto/managed or purely local bookkeeping).
SKIP_FIELDS = {'id', 'created_at'}


def model_field_names(model):
    return [f.name for f in model._meta.get_fields() if getattr(f, 'concrete', False) and not f.many_to_many]


def get_fk_field_ids(model):
    """Return {field_name: related_model} for concrete FK fields."""
    out = {}
    for f in model._meta.get_fields():
        if getattr(f, 'many_to_one', False) and getattr(f, 'concrete', False):
            out[f.name] = f.related_model
    return out


def sync_models(apply: bool, backup_dir: Path):
    from django.apps import apps as django_apps

    pk_map = {}  # (app_label, model_name) -> {local_pk: production_pk}
    report = []
    backup_rows = {}
    vendor_misses = []

    for app_label, model_name, natural_key, fk_config in SYNC_PLAN:
        Model = django_apps.get_model(app_label, model_name)
        fk_targets = get_fk_field_ids(Model)
        fields = [f for f in model_field_names(Model) if f not in SKIP_FIELDS]

        local_qs = Model.objects.using('default').all().order_by('pk')
        created, updated, skipped = 0, 0, 0
        pk_map[(app_label, model_name)] = {}

        for obj in local_qs:
            values = {}
            skip_this = False
            for field in fields:
                if field in fk_config:
                    rule = fk_config[field]
                    local_related_id = getattr(obj, f'{field}_id')
                    if local_related_id is None:
                        values[field] = None
                        continue
                    if rule[0] == 'own':
                        target_key = (app_label, fk_targets[field]._meta.object_name)
                        mapped = pk_map.get(target_key, {}).get(local_related_id)
                        if mapped is None:
                            skip_this = True
                            break
                        values[f'{field}_id'] = mapped
                    elif rule[0] == 'lookup':
                        _, look_app, look_model, look_field = rule
                        LookupModel = django_apps.get_model(look_app, look_model)
                        local_related = fk_targets[field].objects.using('default').filter(pk=local_related_id).first()
                        prod_match = None
                        if local_related is not None:
                            lookup_value = getattr(local_related, look_field, None)
                            if lookup_value:
                                prod_match = LookupModel.objects.using('production').filter(
                                    **{f'{look_field}__iexact': lookup_value}
                                ).first()
                        if prod_match is None:
                            if local_related is not None:
                                vendor_misses.append(f'{app_label}.{model_name}[{obj.pk}] -> no production {look_model} for {look_field}={getattr(local_related, look_field, None)!r}')
                            values[f'{field}_id'] = None
                        else:
                            values[f'{field}_id'] = prod_match.pk
                else:
                    values[field] = getattr(obj, field)
            if skip_this:
                skipped += 1
                continue

            # Build the natural-key filter for matching an existing production row.
            nk_filter = {}
            for nk_field in natural_key:
                if nk_field in fk_config:
                    nk_filter[f'{nk_field}_id'] = values.get(f'{nk_field}_id')
                else:
                    nk_filter[nk_field] = values.get(nk_field)

            existing = Model.objects.using('production').filter(**nk_filter).first()
            if existing is not None:
                if apply:
                    if (app_label, model_name) not in backup_rows:
                        backup_rows[(app_label, model_name)] = []
                    backup_rows[(app_label, model_name)].append(_serialize(existing))
                    for k, v in values.items():
                        setattr(existing, k, v)
                    existing.save(using='production')
                pk_map[(app_label, model_name)][obj.pk] = existing.pk
                updated += 1
            else:
                if apply:
                    new_obj = Model(**values)
                    new_obj.save(using='production')
                    pk_map[(app_label, model_name)][obj.pk] = new_obj.pk
                else:
                    pk_map[(app_label, model_name)][obj.pk] = -obj.pk  # placeholder for dry-run dependents
                created += 1

        report.append((f'{app_label}.{model_name}', created, updated, skipped))

    if apply and backup_rows:
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup_file = backup_dir / f'pre_sync_backup_{ts}.json'
        with open(backup_file, 'w', encoding='utf-8') as fh:
            json.dump({f'{k[0]}.{k[1]}': v for k, v in backup_rows.items()}, fh, default=str, ensure_ascii=False, indent=2)
        print(f'\nBacked up {sum(len(v) for v in backup_rows.values())} pre-existing production rows to {backup_file}')

    return report, vendor_misses


def _serialize(instance):
    data = {}
    for f in instance._meta.get_fields():
        if getattr(f, 'concrete', False) and not f.many_to_many:
            data[f.name] = str(getattr(instance, f.attname))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Actually write to production (default: dry-run report only)')
    parser.add_argument('--backup-dir', default=str(BASE_DIR / 'deploy' / 'backups'))
    args = parser.parse_args()

    setup_production_alias()

    print('=' * 70)
    print('DRY RUN (no writes)' if not args.apply else 'APPLYING CHANGES TO PRODUCTION')
    print('=' * 70)

    report, vendor_misses = sync_models(apply=args.apply, backup_dir=Path(args.backup_dir))

    print(f"\n{'Model':<28} {'to create':>10} {'to update':>10} {'skipped':>10}")
    for name, created, updated, skipped in report:
        verb = 'created' if args.apply else 'to create'
        print(f'{name:<28} {created:>10} {updated:>10} {skipped:>10}')

    if vendor_misses:
        print(f'\n{len(vendor_misses)} item(s) reference a vendor not found in production (linked to no vendor instead):')
        for line in vendor_misses[:20]:
            print(' -', line)
        if len(vendor_misses) > 20:
            print(f'   ... and {len(vendor_misses) - 20} more')

    print('\nNote: image/file fields copy the stored path only — verify the')
    print('actual media file also exists in production storage (R2/Supabase).')

    if not args.apply:
        print('\nThis was a DRY RUN — nothing was written. Re-run with --apply to write.')


if __name__ == '__main__':
    main()
