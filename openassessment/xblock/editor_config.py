"""Open Response available editors configuration"""

from django.conf import settings


editor_overrides = getattr(settings, 'ORA_AVAILABLE_EDITORS', {})

AVAILABLE_EDITORS = {
    'text': {
        'display_name': 'Simple Text Editor',
        'js': ['/static/js/openassessment-editor-textarea.js'],
    },
    'tinymce': {
        'display_name': 'WYSIWYG Editor',
        'js': ['/static/js/openassessment-editor-tinymce.js'],
        'css': ['/static/js/vendor/tinymce/js/tinymce/skins/studio-tmce4/skin.min.css'],
    },
}

AVAILABLE_EDITORS.update(editor_overrides)
