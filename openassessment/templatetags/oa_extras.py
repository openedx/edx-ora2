from django import template
from django.template.defaultfilters import linebreaks, stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from bleach import callbacks

import bleach

register = template.Library()


@register.filter()
@stringfilter
def link_and_linebreak(text):
    """
    Converts URLs in text into clickable links with their target attribute set to `_blank`.
    It wraps givent tags into <p> tags and converts line breaks(\n) to <br> tags.
    Args:
        text: (str) Text having URLs to be converted
    Returns: (str) Text with URLs convert to links
    """
    if text:
        escaped_text = conditional_escape(text)
        return mark_safe(linebreaks(bleach.linkify(escaped_text, callbacks=[callbacks.target_blank])))
