"""
Signals for the workflow API.
See https://docs.djangoproject.com/en/1.4/topics/signals
"""

import django.dispatch

# Indicate that an assessment has completed
# You can fire this signal from asynchronous processes (such as AI grading)
# to notify receivers that an assessment is available.
assessment_complete_signal = django.dispatch.Signal()    # pylint: disable=C0103
