"""Merge static page translations into locale .po files and compile messages."""

import re
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from manager.page_i18n_catalog import PAGE_I18N

TRANS_RE = re.compile(r"""{%\s*trans\s+['"](.+?)['"]\s*%}""")
BLOCKTRANS_RE = re.compile(r"""{%\s*blocktrans\s*%}(.+?){%\s*endblocktrans\s*%}""", re.DOTALL)


def _collect_template_msgids(base_dir):
    roots = [
        base_dir / 'manager' / 'templates' / 'public' / 'pages',
        base_dir / 'manager' / 'templates' / 'includes' / 'home_faq_section.html',
    ]
    found = set()
    for root in roots:
        paths = [root] if root.is_file() else root.rglob('*.html')
        for path in paths:
            text = path.read_text(encoding='utf-8')
            found.update(TRANS_RE.findall(text))
            for block in BLOCKTRANS_RE.findall(text):
                found.add(block.strip())
    return found


class Command(BaseCommand):
    help = 'Extract page strings, merge en/fr translations from catalog, compile messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fill',
            action='store_true',
            help='Fill remaining empty .po entries via OpenRouter API',
        )

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError:
            self.stderr.write(self.style.ERROR('Install polib: pip install polib'))
            return

        self.stdout.write('Running makemessages...')
        try:
            call_command('makemessages', locale=['en', 'fr'], ignore=['venv', '.venv', 'node_modules'], verbosity=0)
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'makemessages skipped ({exc}). Merging catalog into existing .po files.'))

        locale_root = Path(settings.BASE_DIR) / 'locale'
        template_msgids = _collect_template_msgids(Path(settings.BASE_DIR))
        all_msgids = set(PAGE_I18N) | template_msgids
        for lang in ('en', 'fr'):
            po_path = locale_root / lang / 'LC_MESSAGES' / 'django.po'
            if not po_path.exists():
                self.stderr.write(f'Missing {po_path}')
                continue
            po = polib.pofile(str(po_path), encoding='utf-8')
            updated = 0
            added = 0
            for msgid in sorted(all_msgids):
                trans = PAGE_I18N.get(msgid, {})
                text = trans.get(lang, '')
                entry = po.find(msgid)
                if entry:
                    if text and entry.msgstr != text:
                        entry.msgstr = text
                        updated += 1
                else:
                    po.append(polib.POEntry(msgid=msgid, msgstr=text))
                    added += 1
            po.save(str(po_path))
            self.stdout.write(self.style.SUCCESS(f'{lang}: updated {updated}, added {added} (templates: {len(template_msgids)} strings)'))

        self.stdout.write('Compiling messages...')
        compiled = 0
        for lang in ('en', 'fr'):
            po_path = locale_root / lang / 'LC_MESSAGES' / 'django.po'
            mo_path = locale_root / lang / 'LC_MESSAGES' / 'django.mo'
            if po_path.exists():
                po = polib.pofile(str(po_path), encoding='utf-8')
                po.save_as_mofile(str(mo_path))
                compiled += 1
        self.stdout.write(self.style.SUCCESS(f'Compiled {compiled} locale file(s).'))
        self.stdout.write(self.style.SUCCESS('Page i18n sync complete.'))

        if options.get('fill'):
            self.stdout.write('Filling remaining empty translations via OpenRouter...')
            call_command('fill_po_translations', verbosity=1)
            for lang in ('en', 'fr'):
                po_path = locale_root / lang / 'LC_MESSAGES' / 'django.po'
                mo_path = locale_root / lang / 'LC_MESSAGES' / 'django.mo'
                if po_path.exists():
                    polib.pofile(str(po_path), encoding='utf-8').save_as_mofile(str(mo_path))
            self.stdout.write(self.style.SUCCESS('Auto-fill complete.'))
