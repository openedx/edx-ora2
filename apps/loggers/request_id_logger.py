# -*- coding: utf-8 -*- 
"""A custom log handler which knows to insert IDs from request_id middleware"""


import logging

get_request = lambda: None
try:
    from middleware.request_id import get_request
except ImportError:
    pass


class RequestIDLogHandler(logging.StreamHandler):
    """Insert the ID from the SetRequestLogID middleware into the logstream"""
    def __init__(self):
        logging.StreamHandler.__init__(self)

    def emit(self, record):
        try:
            token = getattr(get_request(), 'META', {}).get('HTTP_X_EDX_LOG_TOKEN', '') 
            if token:
                msg = '['+token+'] '+self.format(record)
            msg += "\n"
            self.stream.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
