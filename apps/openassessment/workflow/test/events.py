"""
This is just a dummy event logger to test our ability to dyanmically change this
value based on configuration. All this should go away when we start using the
edx-analytics approved library (once that's ready to be used on prod).
"""

def fake_event_logger(event):
    print event
