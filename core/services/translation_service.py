"""
TranslationService — traduction automatique via OpenRouter.

Primary/fallback models are both free-tier OpenRouter models (see
TRANSLATEBOT_MODEL / TRANSLATEBOT_FALLBACK_MODEL in settings.py).

Usage:
    from core.services.translation_service import TranslationService
    svc = TranslationService()
    en_text = svc.translate("新鲜蔬菜", source='zh', target='en', content_type='product_name')
"""
import logging
from django.conf import settings
from django.utils import translation

logger = logging.getLogger(__name__)

# Prompts par type de contenu (source/target sont injectés dynamiquement)
_PROMPTS = {
    'product_name': (
        "Translate this e-commerce product name from {source} to {target}. "
        "Return ONLY the translation, no explanation: {text}"
    ),
    'product_description': (
        "Translate this marketplace product description from {source} to {target}. "
        "Keep a natural commercial tone. Return ONLY the translation: {text}"
    ),
    'course_title': (
        "Translate this online course title from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'course_description': (
        "Translate this online course description from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'book_name': (
        "Translate this book title from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'book_description': (
        "Translate this book description from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'blog_title': (
        "Translate this blog post title from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'blog_excerpt': (
        "Translate this blog post excerpt/summary from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'blog_content': (
        "Translate this blog post body from {source} to {target}. "
        "Preserve any HTML tags exactly as they are; translate only the text "
        "content. Return ONLY the translation: {text}"
    ),
    'legal': (
        "Translate this legal/formal text from {source} to {target}. "
        "Return ONLY the translation: {text}"
    ),
    'general': (
        "Translate from {source} to {target}. Return ONLY the translation: {text}"
    ),
}

# Noms de langue lisibles pour les prompts
_LANG_NAMES = {
    'zh': 'Chinese (Simplified)',
    'zh-hans': 'Chinese (Simplified)',
    'en': 'English',
    'fr': 'French',
}


class TranslationService:
    """
    Wraps OpenRouter to translate text via Gemma 4 (free).

    Calls the OpenRouter REST API directly with `requests` rather than
    through litellm — litellm's response handling choked on OpenRouter
    responses that arrive with leading whitespace padding (seen in this
    environment as "peer closed connection" / "incomplete chunked read"
    errors even though the raw HTTP call succeeds with a normal 200).
    """

    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        self.model = self._normalize_model(
            getattr(settings, 'TRANSLATEBOT_MODEL', 'nvidia/nemotron-3-ultra-550b-a55b:free')
        )
        self.fallback_model = self._normalize_model(
            getattr(settings, 'TRANSLATEBOT_FALLBACK_MODEL', 'google/gemma-4-31b-it:free')
        )

    @staticmethod
    def _normalize_model(raw_model: str) -> str:
        # Older config carried a litellm-style 'openrouter/' provider prefix —
        # OpenRouter's own REST API expects the bare model id.
        return raw_model[len('openrouter/'):] if raw_model.startswith('openrouter/') else raw_model

    def _call_llm(self, prompt: str, attempts: int = 2) -> str:
        """
        Low-level call to the OpenRouter chat completions API.

        Tries self.model first, then self.fallback_model — both are
        OpenRouter free-tier models and either can be rate-limited or
        temporarily unavailable independently of the other. Each model is
        retried a couple of times first, since this dev environment routes
        outbound HTTPS through a local proxy (Clash/mihomo) that
        intermittently drops connections mid-request — a single failed
        attempt isn't a reliable signal that a model is actually unusable.
        """
        import requests
        import time
        last_exc = None
        for model in (self.model, self.fallback_model):
            if not model:
                continue
            for attempt in range(attempts):
                try:
                    resp = requests.post(
                        'https://openrouter.ai/api/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {self.api_key}',
                            'Content-Type': 'application/json',
                        },
                        json={
                            'model': model,
                            'messages': [{'role': 'user', 'content': prompt}],
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data['choices'][0]['message']['content'].strip()
                except Exception as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        time.sleep(1.5 * (attempt + 1))
        logger.error("TranslationService error (tried %s, %s): %s", self.model, self.fallback_model, last_exc)
        return ""

    def translate(
        self,
        text: str,
        source: str = 'zh-hans',
        target: str = 'en',
        content_type: str = 'general',
    ) -> str:
        """
        Translate *text* from *source* language to *target* language.

        Returns empty string on failure (never raises).
        """
        if not text or not text.strip():
            return text

        if not self.api_key:
            logger.warning("TranslationService: OPENROUTER_API_KEY not set — skipping.")
            return ""

        src_name = _LANG_NAMES.get(source, source)
        tgt_name = _LANG_NAMES.get(target, target)
        template = _PROMPTS.get(content_type, _PROMPTS['general'])
        prompt = template.format(source=src_name, target=tgt_name, text=text)

        return self._call_llm(prompt)

    def translate_fields(
        self,
        text: str,
        source: str = 'zh-hans',
        targets: tuple = ('en', 'fr'),
        content_type: str = 'general',
    ) -> dict:
        """
        Convenience wrapper — returns {lang: translation} for all *targets*.
        """
        return {lang: self.translate(text, source, lang, content_type) for lang in targets}


# Languages configured in MODELTRANSLATION_LANGUAGES; kept in sync manually
# since modeltranslation field names are derived from these at import time.
_MT_LANGUAGES = ('zh-hans', 'en', 'fr')


def _mt_suffix(lang_code: str) -> str:
    """modeltranslation field-name suffix for a language code ('zh-hans' -> 'zh_hans')."""
    return lang_code.replace('-', '_')


def auto_translate_new_instance(instance, model_cls, field_specs, languages=_MT_LANGUAGES):
    """
    Post-save hook for newly-created translatable model instances: fills in
    the *other* configured languages by machine-translating from whichever
    language the content was actually entered in.

    Deliberately does NOT assume the source is MODELTRANSLATION_DEFAULT_LANGUAGE
    ('zh-hans') — vendor/admin forms are submitted with whatever Django
    language is active for that request (LocaleMiddleware negotiates this;
    since LANGUAGE_CODE='fr', that's usually 'fr', not 'zh-hans'), and
    `instance.<field> = value` writes into the column for *that* active
    language. Using the real active language as source avoids reading an
    empty zh_hans column and treating the item as untranslatable.

    Never overwrites a field that already holds text (the source field, or
    any target field populated some other way), and only writes a target
    field when translate() actually returns something — translate() returns
    "" on missing API key or any failure, so a failed call is a no-op here
    instead of clobbering good data with blanks.

    field_specs: list of (base_field_name, content_type) tuples, e.g.
        [('name', 'product_name'), ('description', 'product_description')]
    """
    current_lang = translation.get_language()
    if current_lang not in languages:
        current_lang = getattr(settings, 'LANGUAGE_CODE', 'fr')
    if current_lang not in languages:
        current_lang = languages[0]
    source_suffix = _mt_suffix(current_lang)

    svc = TranslationService()
    update_kwargs = {}
    for base_field, content_type in field_specs:
        source_field = f'{base_field}_{source_suffix}'
        source_text = getattr(instance, source_field, '') or getattr(instance, base_field, '')
        if not source_text:
            continue
        for lang in languages:
            if lang == current_lang:
                continue
            target_field = f'{base_field}_{_mt_suffix(lang)}'
            if getattr(instance, target_field, ''):
                continue  # already has content, don't overwrite
            translated = svc.translate(source_text, current_lang, lang, content_type)
            if translated:
                update_kwargs[target_field] = translated

    if update_kwargs:
        model_cls.objects.filter(pk=instance.pk).update(**update_kwargs)
    return update_kwargs
