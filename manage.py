#!/usr/bin/env python
import sys
import os

if __name__ == "__main__":

    # Default to dev settings for convenience
    if os.environ.get('DJANGO_SETTINGS_MODULE') is None:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.dev'

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
