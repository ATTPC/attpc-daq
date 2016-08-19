import logging
from .models import LogEntry


class DjangoDatabaseHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            entry = LogEntry(name=record.name,
                             create_time=record.created,
                             level_number=record.levelno,
                             level_name=record.levelname,
                             path_name=record.pathname,
                             line_num=record.lineno,
                             function_name=record.funcName,
                             message=record.getMessage())
            entry.save()
        except Exception:
            self.handleError(record)
