#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    # For convenience, use the test-specific settings by default
    # when running nose or lettuce test suites.
    # Otherwise, use the base settings.
    if 'test' in sys.argv or 'harvest' in sys.argv:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.test")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.dev")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

    # Execute JavaScript tests
    if 'test' in sys.argv:
        os.system('npm install && npm test')
