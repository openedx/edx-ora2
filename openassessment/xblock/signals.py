from __future__ import absolute_import

from django.dispatch import Signal

# Indicates that all the test cases against a problem have been evaluated
CODING_TEST_CASES_EVALUATED = Signal(providing_args=[
    'submission_uuid',  # Submission instance's uuid
    'block_id',         # Block id (or question) for which the evaluation has completed
])
