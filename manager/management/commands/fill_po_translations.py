"""
management command: fill_po_translations
=========================================
Traduit les entrées vides des fichiers .po (locale/en/ et locale/fr/)
via OpenRouter API (appel requests direct, sans litellm), en mode batch.

Usage:
    python manage.py fill_po_translations
    python manage.py fill_po_translations --lang en
    python manage.py fill_po_translations --lang fr
    python manage.py fill_po_translations --dry-run
    python manage.py fill_po_translations --overwrite
"""

import time
import json
import logging
from pathlib import Path
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 6
BASE_WAIT = 20
BATCH_SIZE = 15  # strings per API call

LANG_NAMES = {'en': 'English', 'fr': 'French'}


def _call_openrouter(api_key, model, prompt):
    """HTTP call to OpenRouter with retry."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://duno360.com",
        "X-Title": "DUNO360 Translation",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.1,
    }
    wait = BASE_WAIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=45)
            if resp.status_code == 429:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Rate limit attempt {attempt}, waiting {wait}s")
                    time.sleep(wait)
                    wait = min(wait * 2, 180)
                    continue
                resp.raise_for_status()
            elif resp.status_code in (502, 503, 504):
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    wait = min(wait * 2, 120)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'].strip()
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(wait)
                wait = min(wait * 2, 120)
            else:
                raise
    return ''


def _translate_batch(api_key, model, strings, lang_name):
    """Translate a numbered list of strings in a single API call."""
    numbered = '\n'.join(f'{i+1}. {s}' for i, s in enumerate(strings))
    prompt = (
        f"Translate these UI strings to {lang_name}.\n"
        f"IMPORTANT:\n"
        f"- Reply with ONLY numbered translations, one per line: '1. <translation>'\n"
        f"- Keep HTML tags, {{{{ variables }}}}, and %s/%d placeholders exactly as-is\n"
        f"- Keep brand names (DUNO 360, ScholarQuest) unchanged\n"
        f"- If a string is already in {lang_name}, keep it unchanged\n"
        f"- Do not add any explanation\n\n"
        f"Strings:\n{numbered}"
    )
    raw = _call_openrouter(api_key, model, prompt)
    if not raw:
        return strings  # fallback

    results = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        for sep in ('. ', ') ', ': '):
            if sep in line:
                parts = line.split(sep, 1)
                try:
                    idx = int(parts[0].rstrip('.):')) - 1
                    if 0 <= idx < len(strings):
                        results[idx] = parts[1].strip()
                    break
                except ValueError:
                    pass

    return [results.get(i, strings[i]) for i in range(len(strings))]


class Command(BaseCommand):
    help = 'Fill empty .po msgstr entries via OpenRouter (batch mode, no litellm)'

    def add_arguments(self, parser):
        parser.add_argument('--lang', dest='langs', action='append',
                            help='Target language code (en, fr). Default: all.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--overwrite', action='store_true')
        parser.add_argument('--llm-model', dest='llm_model', default=None)

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError:
            self.stderr.write('polib not installed: pip install polib')
            return

        api_key = (
            getattr(settings, 'OPENROUTER_API_KEY', '')
            or getattr(settings, 'TRANSLATEBOT_API_KEY', '')
        )
        if not api_key:
            self.stderr.write(self.style.ERROR('OPENROUTER_API_KEY not set'))
            return

        raw_model = (
            options.get('llm_model')
            or getattr(settings, 'TRANSLATEBOT_MODEL', 'meta-llama/llama-4-scout:free')
        )
        llm_model = raw_model.replace('openrouter/', '', 1)

        target_langs = options['langs'] or list(LANG_NAMES.keys())
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        self.stdout.write(f'fill_po_translations | model={llm_model} | langs={target_langs}')

        locale_root = Path(settings.BASE_DIR) / 'locale'

        for lang in target_langs:
            po_path = locale_root / lang / 'LC_MESSAGES' / 'django.po'
            if not po_path.exists():
                self.stderr.write(f'Not found: {po_path}')
                continue

            self.stdout.write(f'\nProcessing {lang} -> {po_path}')
            po = polib.pofile(str(po_path), encoding='utf-8')

            if overwrite:
                to_translate = [e for e in po if e.msgid and not e.obsolete]
            else:
                to_translate = [e for e in po if e.msgid and not e.msgstr and not e.obsolete]

            self.stdout.write(f'  {len(to_translate)} entries to translate')

            if dry_run or not to_translate:
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] would translate {len(to_translate)} entries')
                continue

            lang_name = LANG_NAMES.get(lang, lang)
            translated_count = 0
            error_count = 0

            for batch_start in range(0, len(to_translate), BATCH_SIZE):
                batch = to_translate[batch_start:batch_start + BATCH_SIZE]
                batch_end = min(batch_start + BATCH_SIZE, len(to_translate))
                self.stdout.write(
                    f'  Batch {batch_start + 1}-{batch_end}/{len(to_translate)}...',
                    ending=''
                )
                self.stdout.flush()

                try:
                    translations = _translate_batch(
                        api_key, llm_model,
                        [e.msgid for e in batch], lang_name
                    )
                    for entry, translated in zip(batch, translations):
                        if translated and translated.strip():
                            entry.msgstr = translated
                            translated_count += 1
                    po.save(str(po_path))
                    self.stdout.write(f' ok ({translated_count} done so far)')
                    time.sleep(1.5)
                except Exception as exc:
                    self.stdout.write('')
                    self.stderr.write(self.style.WARNING(f'  Batch failed: {exc}'))
                    error_count += len(batch)

            self.stdout.write(self.style.SUCCESS(
                f'  {lang}: {translated_count} translated, {error_count} errors'
            ))

        self.stdout.write(self.style.SUCCESS('\nAll .po files processed.'))
        self.stdout.write('Now run: python manage.py compilemessages')

