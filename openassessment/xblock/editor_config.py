"""Open Response available editors configuration"""

from django.conf import settings


external_editors = getattr(settings, 'ORA_AVAILABLE_EDITORS', {})

default_editors = {
    'text': {
        'display_name': 'Simple Text Editor',
        'js': ['/xblock/resource/openassessment/static/js/openassessment-editor-textarea.js'],
    },
    'tinymce': {
        'display_name': 'WYSIWYG Editor',
        'js': ['/xblock/resource/openassessment/static/js/openassessment-editor-tinymce.js'],
    },
}

AVAILABLE_EDITORS = {}
AVAILABLE_EDITORS.update(external_editors)
AVAILABLE_EDITORS.update(default_editors)
