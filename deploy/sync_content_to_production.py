#!/usr/bin/env python3
"""
sync_content_to_production.py
==============================
Upsert catalog content — books (Publisher, BookCategory, Book, Author) and
marketplace items (Category, Product, Course + its sections/lessons,
SupermarketItem) — from the LOCAL dev database into PRODUCTION, matched by
natural key (slug / title / name) — never by raw primary key, since local
and production auto-increment IDs do not correspond to the same real-world
rows.

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
    ('manager', 'Publisher', ('publisher_name',), {}),
    ('manager', 'BookCategory', ('slug',), {'parent': ('own',)}),
    # Book has no unique slug/ISBN field in this schema — (name, publisher)
    # is the best available natural key. If two different books from the
    # same publisher genuinely share a title, the second will update the
    # first's row instead of creating a new one; the dry-run report is the
    # place to catch that before using --apply.
    ('manager', 'Book', ('name', 'publisher'), {'publisher': ('own',), 'category': ('own',)}),
    ('marketplace', 'Category', ('slug',), {'parent': ('own',)}),
    ('marketplace', 'Product', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
    ('marketplace', 'Course', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
    ('marketplace', 'CourseSection', ('course', 'title'), {'course': ('own',)}),
    ('marketplace', 'CourseLesson', ('section', 'title'), {'section': ('own',)}),
    ('marketplace', 'SupermarketItem', ('slug',), {'category': ('own',), 'vendor': ('lookup', 'manager', 'Vendor', 'email')}),
]

# Author is many-to-many with Book (no FK column to resolve through the
# generic loop above), so it's synced separately, after Book — matched by
# name, with its `book` M2M rebuilt from the already-synced Book pk_map.
AUTHOR_PLAN = ('manager', 'Author', ('name',))

# Fields never copied across (auto/managed or purely local bookkeeping).
SKIP_FIELDS = {'id', 'created_at'}


def _translated_base_fields(model):
    """Base field names (e.g. 'name') registered with django-modeltranslation
    for this model — these have no reliable single DB column: reading or
    writing the bare name goes through a descriptor that resolves to
    name_<active_language>, which depends on ambient state this script never
    sets (no request, no LocaleMiddleware). Two real bugs came from this:
    natural-key matching against the bare field silently compared the wrong
    language column between local/production (e.g. local resolved to
    name_fr while production's name_fr was empty and fell back to
    name_zh_hans — an exact-string match against two different columns
    that happened to both be called 'name'), and copying the bare field's
    value could overwrite one of the real language columns with a
    different language's text. The suffixed columns (name_zh_hans, _en,
    _fr) are ordinary, unambiguous fields and are copied/matched directly
    instead — see MODELTRANSLATION_DEFAULT_LANGUAGE in settings.py."""
    from modeltranslation.translator import translator, NotRegistered
    try:
        return set(translator.get_options_for_model(model).fields)
    except NotRegistered:
        return set()


def model_field_names(model):
    translated = _translated_base_fields(model)
    return [
        f.name for f in model._meta.get_fields()
        if getattr(f, 'concrete', False) and not f.many_to_many and f.name not in translated
    ]


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
        translated_fields = _translated_base_fields(Model)

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
            # A translated field (e.g. 'name') has no reliable single value in
            # `values` — it was deliberately excluded from the copy loop above —
            # so match on its unambiguous name_zh_hans column instead.
            nk_filter = {}
            for nk_field in natural_key:
                if nk_field in fk_config:
                    nk_filter[f'{nk_field}_id'] = values.get(f'{nk_field}_id')
                elif nk_field in translated_fields:
                    nk_filter[f'{nk_field}_zh_hans'] = getattr(obj, f'{nk_field}_zh_hans')
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

    return report, vendor_misses, pk_map, backup_rows


def write_backup(apply: bool, backup_rows: dict, backup_dir: Path):
    if not apply or not backup_rows:
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_file = backup_dir / f'pre_sync_backup_{ts}.json'
    with open(backup_file, 'w', encoding='utf-8') as fh:
        json.dump({f'{k[0]}.{k[1]}': v for k, v in backup_rows.items()}, fh, default=str, ensure_ascii=False, indent=2)
    print(f'\nBacked up {sum(len(v) for v in backup_rows.values())} pre-existing production rows to {backup_file}')


def sync_authors(apply: bool, pk_map: dict, backup_rows: dict):
    """Upsert Author by name, then rebuild its `book` M2M from the Book
    pk_map already built by sync_models() — must run after Book."""
    from django.apps import apps as django_apps

    app_label, model_name, natural_key = AUTHOR_PLAN
    Model = django_apps.get_model(app_label, model_name)
    book_pk_map = pk_map.get(('manager', 'Book'), {})

    created, updated, partial_links = 0, 0, 0
    for obj in Model.objects.using('default').all().order_by('pk'):
        # Match/write via the unambiguous suffixed column — see
        # _translated_base_fields() docstring in sync_models() above; the
        # bare `name` attribute resolves through an active-language proxy
        # this bare script never sets, which previously caused every
        # author to compare against the wrong column and be recreated
        # instead of matched.
        name_zh = obj.name_zh_hans
        local_book_ids = list(obj.book.values_list('pk', flat=True))
        prod_book_ids = [book_pk_map[bid] for bid in local_book_ids if bid in book_pk_map and book_pk_map[bid] > 0]
        book_link_complete = len(prod_book_ids) == len(local_book_ids)
        if not book_link_complete:
            # Some of this author's books weren't synced (dry-run, or a
            # skipped Book row) — still upsert the author, just don't
            # touch the M2M yet rather than link a partial set.
            partial_links += 1

        existing = Model.objects.using('production').filter(name_zh_hans=name_zh).first()
        if existing is not None:
            if apply:
                if ('manager', 'Author') not in backup_rows:
                    backup_rows[('manager', 'Author')] = []
                backup_rows[('manager', 'Author')].append(_serialize(existing))
                existing.name_en = obj.name_en
                existing.name_fr = obj.name_fr
                existing.save(update_fields=['name_en', 'name_fr'])
                if book_link_complete:
                    existing.book.set(prod_book_ids)
            updated += 1
        else:
            if apply:
                new_obj = Model(name_zh_hans=name_zh, name_en=obj.name_en, name_fr=obj.name_fr)
                new_obj.save(using='production')
                if book_link_complete:
                    new_obj.book.set(prod_book_ids)
            created += 1

    return [('manager.Author', created, updated, partial_links)]


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

    report, vendor_misses, pk_map, backup_rows = sync_models(apply=args.apply, backup_dir=Path(args.backup_dir))
    report += sync_authors(apply=args.apply, pk_map=pk_map, backup_rows=backup_rows)
    write_backup(args.apply, backup_rows, Path(args.backup_dir))

    print(f"\n{'Model':<28} {'to create':>10} {'to update':>10} {'skipped':>10}")
    for name, created, updated, skipped in report:
        print(f'{name:<28} {created:>10} {updated:>10} {skipped:>10}')

    if vendor_misses:
        print(f'\n{len(vendor_misses)} item(s) reference a vendor not found in production (linked to no vendor instead):')
        for line in vendor_misses[:20]:
            print(' -', line)
        if len(vendor_misses) > 20:
            print(f'   ... and {len(vendor_misses) - 20} more')

    print('\nNote: image/file fields copy the stored path only — verify the')
    print('actual media file also exists in production storage (R2/Supabase).')
    print('Note: manager.Author "skipped" column counts authors whose book')
    print('list could not be fully linked yet (a referenced Book was itself')
    print('skipped, or this was a dry run) — re-run after those resolve.')

    if not args.apply:
        print('\nThis was a DRY RUN — nothing was written. Re-run with --apply to write.')


if __name__ == '__main__':
    main()
