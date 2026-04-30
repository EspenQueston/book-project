"""
management command: fill_translations
======================================
Traduit tous les champs DB vides (name_en, name_fr, description_en, etc.)
via OpenRouter API (appel requests direct, sans litellm).
Mode batch : plusieurs enregistrements par appel API.

Usage:
    python manage.py fill_translations
    python manage.py fill_translations --lang en
    python manage.py fill_translations --lang fr
    python manage.py fill_translations --dry-run
    python manage.py fill_translations --overwrite
    python manage.py fill_translations --model Book
"""

import time
import logging
import importlib
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 6
BASE_WAIT = 20  # seconds, doubles on each retry
BATCH_SIZE = 10  # records per API call (for fields like name/title)
DESCRIPTION_BATCH = 3  # fewer for long text fields

MODEL_CONFIGS = [
    {
        'import': ('manager.models', 'Book'),
        'label': 'Book',
        'source': 'zh-hans',
        'fields': [('name', 'book title'), ('description', 'book description')],
    },
    {
        'import': ('manager.models', 'Publisher'),
        'label': 'Publisher',
        'source': 'zh-hans',
        'fields': [('publisher_name', 'publisher name'), ('publisher_address', 'address')],
    },
    {
        'import': ('manager.models', 'Author'),
        'label': 'Author',
        'source': 'zh-hans',
        'fields': [('name', 'person name')],
    },
    {
        'import': ('manager.models', 'BlogPost'),
        'label': 'BlogPost',
        'source': 'auto',
        'fields': [('title', 'blog title'), ('excerpt', 'short excerpt'), ('content', 'blog article')],
    },
    {
        'import': ('marketplace.models', 'Category'),
        'label': 'Category',
        'source': 'zh-hans',
        'fields': [('name', 'category name'), ('description', 'category description')],
    },
    {
        'import': ('marketplace.models', 'Product'),
        'label': 'Product',
        'source': 'zh-hans',
        'fields': [('name', 'product name'), ('description', 'product description')],
    },
    {
        'import': ('marketplace.models', 'Course'),
        'label': 'Course',
        'source': 'zh-hans',
        'fields': [('title', 'course title'), ('description', 'course description')],
    },
    {
        'import': ('marketplace.models', 'SupermarketItem'),
        'label': 'SupermarketItem',
        'source': 'zh-hans',
        'fields': [('name', 'product name'), ('description', 'product description')],
    },
]


def _detect_lang(text):
    """Heuristic: ratio of CJK chars determines if text is Chinese."""
    if not text:
        return 'zh-hans'
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return 'zh-hans' if (cjk / max(len(text), 1)) > 0.1 else 'en'


def _call_openrouter(api_key, model, prompt, max_tokens=1024):
    """Direct HTTP call to OpenRouter with exponential backoff on rate limits."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://duno360.com",
        "X-Title": "DUNO360 Translation",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    wait = BASE_WAIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=45)
            if resp.status_code == 429:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Rate limit (attempt {attempt}), waiting {wait}s")
                    time.sleep(wait)
                    wait = min(wait * 2, 180)
                    continue
                resp.raise_for_status()
            elif resp.status_code in (502, 503, 504):
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    wait = min(wait * 2, 180)
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content'].strip()
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(wait)
                wait = min(wait * 2, 180)
            else:
                raise
    return ''


def _translate_batch(api_key, model, texts, source_lang_name, target_lang_name, content_type, long_text=False):
    """Translate a list of texts in one API call. Returns list of translations."""
    numbered = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
    prompt = (
        f"Translate these {content_type} entries from {source_lang_name} to {target_lang_name}.\n"
        f"Rules:\n"
        f"- Reply with ONLY numbered translations: '1. <translation>'\n"
        f"- Keep proper nouns, brand names, HTML tags unchanged\n"
        f"- Preserve line breaks in long texts\n"
        f"- Do NOT add explanations or quotes\n\n"
        f"Entries:\n{numbered}"
    )
    max_tokens = 2048 if long_text else 1024
    raw = _call_openrouter(api_key, model, prompt, max_tokens=max_tokens)
    if not raw:
        return texts  # fallback: return originals

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
                    if 0 <= idx < len(texts):
                        results[idx] = parts[1].strip()
                    break
                except ValueError:
                    pass
    return [results.get(i, texts[i]) for i in range(len(texts))]


def _detect_lang(text):
    """Heuristic: ratio of CJK chars determines if text is Chinese."""
    if not text:
        return 'zh-hans'
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return 'zh-hans' if (cjk / max(len(text), 1)) > 0.1 else 'en'


class Command(BaseCommand):
    help = 'Fill empty DB translation fields for all registered models via OpenRouter (batched)'

    def add_arguments(self, parser):
        parser.add_argument('--lang', dest='langs', action='append',
                            help='Target language (en, fr). Repeatable. Default: all.')
        parser.add_argument('--model', dest='models', action='append',
                            help='Model label to process (e.g. Book). Default: all.')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--overwrite', action='store_true',
                            help='Re-translate fields that already have a value.')
        parser.add_argument('--llm-model', dest='llm_model', default=None,
                            help='OpenRouter model slug.')

    def handle(self, *args, **options):
        api_key = (
            getattr(settings, 'OPENROUTER_API_KEY', '')
            or getattr(settings, 'TRANSLATEBOT_API_KEY', '')
        )
        if not api_key:
            self.stderr.write(self.style.ERROR('OPENROUTER_API_KEY not set in settings/.env'))
            return

        raw_model = (
            options.get('llm_model')
            or getattr(settings, 'TRANSLATEBOT_MODEL', 'openai/gpt-oss-20b:free')
        )
        llm_model = raw_model.replace('openrouter/', '', 1)

        target_langs = options['langs'] or ['en', 'fr']
        filter_models = options['models'] or []
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        self.stdout.write(self.style.SUCCESS(
            f'fill_translations | model={llm_model} | langs={target_langs} | dry_run={dry_run}'
        ))

        lang_names = {'en': 'English', 'fr': 'French', 'zh-hans': 'Simplified Chinese'}
        total_translated = 0
        total_skipped = 0
        total_errors = 0

        for cfg in MODEL_CONFIGS:
            if filter_models and cfg['label'] not in filter_models:
                continue

            module_name, class_name = cfg['import']
            module = importlib.import_module(module_name)
            Model = getattr(module, class_name)
            source_lang_cfg = cfg['source']

            self.stdout.write(f'\n--- {cfg["label"]} ---')

            for (field, content_type) in cfg['fields']:
                is_long = content_type in ('blog article', 'book description', 'product description',
                                           'course description', 'category description')
                batch_sz = DESCRIPTION_BATCH if is_long else BATCH_SIZE

                for lang in target_langs:
                    target_field = f'{field}_{lang}'

                    # Collect records needing translation
                    work = []  # list of (obj, source_text)
                    for obj in Model.objects.all():
                        if not hasattr(obj, target_field):
                            continue

                        # Determine source text
                        if source_lang_cfg == 'auto':
                            base = getattr(obj, field, '') or ''
                            src_zh = getattr(obj, f'{field}_zh_hans', None) or ''
                            src_en = getattr(obj, f'{field}_en', None) or ''
                            detected = _detect_lang(base)
                            source_lang_actual = detected
                            source_text = (src_zh or base) if detected == 'zh-hans' else (src_en or base)
                        else:
                            source_lang_actual = source_lang_cfg
                            src_field = f'{field}_zh_hans' if source_lang_cfg == 'zh-hans' else f'{field}_{source_lang_cfg}'
                            source_text = getattr(obj, src_field, None) or getattr(obj, field, '') or ''

                        if lang == source_lang_actual:
                            continue
                        if not source_text or not source_text.strip():
                            continue

                        current = getattr(obj, target_field, None)
                        if current and str(current) not in ('None', '') and not overwrite:
                            total_skipped += 1
                            continue

                        work.append((obj, source_text, source_lang_actual))

                    if not work:
                        continue

                    self.stdout.write(
                        f'  {cfg["label"]}.{field} -> {lang}: {len(work)} records to translate'
                    )

                    if dry_run:
                        total_translated += len(work)
                        continue

                    # --- BATCH TRANSLATE ---
                    for batch_start in range(0, len(work), batch_sz):
                        batch = work[batch_start:batch_start + batch_sz]
                        texts = [item[1] for item in batch]
                        src_lang_name = lang_names.get(batch[0][2], batch[0][2])
                        tgt_lang_name = lang_names.get(lang, lang)

                        try:
                            translations = _translate_batch(
                                api_key, llm_model,
                                texts, src_lang_name, tgt_lang_name,
                                content_type, long_text=is_long
                            )
                            for (obj, _, _), translated in zip(batch, translations):
                                if translated and translated.strip():
                                    Model.objects.filter(pk=obj.pk).update(**{target_field: translated})
                                    total_translated += 1
                            self.stdout.write(
                                f'    batch {batch_start + 1}-{batch_start + len(batch)}: '
                                f'{len(translations)} translations saved'
                            )
                            time.sleep(1.5)
                        except Exception as exc:
                            self.stderr.write(
                                self.style.WARNING(f'    batch error: {exc}')
                            )
                            total_errors += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. translated={total_translated} '
            f'skipped={total_skipped} errors={total_errors}'
        ))

