"""Compile .po → .mo using polib (no GNU msgfmt required)."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Compile locale message files using polib (Windows-friendly, no msgfmt).'

    def add_arguments(self, parser):
        parser.add_argument(
            '-l', '--locale', action='append', dest='locales',
            help='Locale(s) to compile, e.g. en fr',
        )

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError as exc:
            raise CommandError('polib is required: pip install polib') from exc

        locales = options.get('locales') or [code for code, _ in settings.LANGUAGES if code != settings.LANGUAGE_CODE]
        base = Path(settings.BASE_DIR) / 'locale'
        compiled = 0

        for locale in locales:
            po_dir = base / locale / 'LC_MESSAGES'
            if not po_dir.is_dir():
                self.stderr.write(self.style.WARNING(f'Skipping missing locale: {locale}'))
                continue
            for po_path in po_dir.glob('*.po'):
                mo_path = po_path.with_suffix('.mo')
                po = polib.pofile(str(po_path), encoding='utf-8')
                po.save_as_mofile(str(mo_path))
                compiled += 1
                self.stdout.write(self.style.SUCCESS(f'Compiled {po_path.relative_to(base)} -> {mo_path.name}'))

        if not compiled:
            raise CommandError('No .po files compiled.')
        self.stdout.write(self.style.SUCCESS(f'Done — {compiled} file(s).'))
