import markdown as md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='markdown')
def markdown_filter(value):
    """Convert Markdown text to HTML."""
    if not value:
        return ''
    html = md.markdown(
        value,
        extensions=['extra', 'codehilite', 'toc', 'nl2br', 'sane_lists'],
    )
    return mark_safe(html)
