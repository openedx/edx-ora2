"""Open Response available editors configuration"""

from django.conf import settings


editor_overrides = getattr(settings, 'ORA_AVAILABLE_EDITORS', {})

AVAILABLE_EDITORS = {
    'text': {
        'display': 'Simple Text Editor',
        'js': ['js/openassessment-editor-textarea.js'],
    },
    'tinymce': {
        'id': 'tinymce',
        'display': 'WYSIWYG Editor',
        'js': ['js/openassessment-editor-tinymce.js'],
    },
}

AVAILABLE_EDITORS.update(editor_overrides)
