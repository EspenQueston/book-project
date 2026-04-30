"""
TranslationService — traduction automatique via OpenRouter / Gemma 4.

Phase dev  : google/gemma-4-31b-it:free  (100 % gratuit, sans quota)
Phase prod : remplacer le modèle par gemini/gemini-2.5-pro ou qwen/qwen3

Usage:
    from core.services.translation_service import TranslationService
    svc = TranslationService()
    en_text = svc.translate("新鲜蔬菜", source='zh', target='en', content_type='product_name')
"""
import logging
from django.conf import settings

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

    The service is lazy — it only imports litellm and creates the client
    when translate() is first called, so importing this module is cheap.
    """

    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        # TRANSLATEBOT_MODEL already includes 'openrouter/' prefix (e.g. 'openrouter/google/gemma-4-31b-it:free')
        raw_model = getattr(settings, 'TRANSLATEBOT_MODEL', 'openrouter/google/gemma-4-31b-it:free')
        # Normalize: ensure single 'openrouter/' prefix
        self.model = raw_model if raw_model.startswith('openrouter/') else f"openrouter/{raw_model}"

    def _call_llm(self, prompt: str) -> str:
        """Low-level call to litellm via OpenRouter."""
        try:
            import litellm
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                api_base="https://openrouter.ai/api/v1",
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("TranslationService error: %s", exc)
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
