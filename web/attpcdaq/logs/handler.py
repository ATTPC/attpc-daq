import logging
from datetime import datetime


class DjangoDatabaseHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        from .models import LogEntry
        try:
            entry = LogEntry(logger_name=record.name,
                             create_time=datetime.fromtimestamp(record.created),
                             level=record.levelno,
                             path_name=record.pathname,
                             line_num=record.lineno,
                             function_name=record.funcName,
                             message=record.getMessage(),
                             traceback=record.exc_text)
            entry.save()
        except Exception:
            self.handleError(record)
