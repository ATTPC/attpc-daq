import logging
logger = logging.getLogger('attpcdaq')
for handler in logger.handlers:
    logger.removeHandler(handler)
