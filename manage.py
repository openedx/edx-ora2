#!/usr/bin/env python
import sys
import os

if __name__ == "__main__":

    if os.environ.get('DJANGO_SETTINGS_MODULE') is None:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.base'

    # When using an on-disk database for the test suite,
    # Django asks us if we want to delete the database.
    # We do.
    if 'test' in sys.argv[0:3]:
        # Catch warnings in tests and redirect them to be handled by the test runner. Otherwise build results are too
        # noisy to be of much use.
        import logging
        logging.captureWarnings(True)
        sys.argv.append('--noinput')

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
