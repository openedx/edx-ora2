from django import template
from django.template.defaultfilters import linebreaks, stringfilter
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from bleach import callbacks

import bleach

register = template.Library()


@register.filter(needs_autoescape=True)
@stringfilter
def link_and_linebreak(text, autoescape=True):

    if text and len(text) > 0:
        the_text = conditional_escape(text)
        return mark_safe(linebreaks(bleach.linkify(the_text, callbacks=[callbacks.target_blank])))
    else:
        return text
