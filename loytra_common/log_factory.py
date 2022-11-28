import sys
import logging
import logging.handlers

_glob_log_timestamp: bool = True
_loggers: dict[str, tuple[logging.Logger, logging.StreamHandler, str]] = { }

def _create_handler(tag: str):
    handler = logging.StreamHandler(sys.stdout)
    logFormatter = _CustomFormatter(tag, _glob_log_timestamp)
    handler.setFormatter(logFormatter)
    return handler

def set_log_timestamp(enable: bool):
    global _glob_log_timestamp, _loggers
    if _glob_log_timestamp != enable:
        _glob_log_timestamp = enable

        _loggers_copy = _loggers.copy()
        for name, logger_info in _loggers_copy.items():
            logger, old_handler, tag = logger_info
            logger.removeHandler(old_handler)

            new_handler = _create_handler(tag)
            logger.addHandler(new_handler)
            _loggers[name] = (logger, new_handler, tag)


class _CustomFormatter(logging.Formatter):
    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    green = "\033[92m"
    reset = '\x1b[0m'

    def make_fmt(self, color, level, log_timestamp):
        parts = []

        # timestamp
        if log_timestamp:
            parts.append("[%(asctime)s.%(msecs)03d]")

        # level
        parts.append("[" + color + level + self.reset + "]")

        # tag
        if len(self._tag_name) > 0:
            parts.append("[" + self._tag_name + "]")

        # message
        parts.append(": %(message)s")

        return "".join(parts)

    def create_formatters(self, log_timestamp: bool):
        date_fmt = "%d.%m %H:%M:%S"
        self.formatters = {
            logging.DEBUG: logging.Formatter(self.make_fmt(self.blue, "DBG", log_timestamp), datefmt=date_fmt),
            logging.INFO: logging.Formatter(self.make_fmt(self.green, "INF", log_timestamp), datefmt=date_fmt),
            logging.WARNING: logging.Formatter(self.make_fmt(self.yellow, "WRN", log_timestamp), datefmt=date_fmt),
            logging.ERROR: logging.Formatter(self.make_fmt(self.red, "ERR", log_timestamp), datefmt=date_fmt),
            logging.CRITICAL: logging.Formatter(self.make_fmt(self.bold_red, "CRT", log_timestamp), datefmt=date_fmt)
        }

    def __init__(self, tag_name: str, log_timestamp: bool):
        super().__init__()
        self._tag_name = tag_name.strip() if tag_name is not None else ""
        self.create_formatters(log_timestamp)

    def format(self, record):
        formatter = self.formatters.get(record.levelno)
        return formatter.format(record) if formatter is not None else record

def get(name = 'main', tag = ''):
    global _loggers
    if name is None:
        name = 'main'

    logger_info = _loggers.get(name)
    logger = None
    if logger_info is not None:
        logger = logger_info[0]

    if logger is None:
        logger = logging.getLogger(name)
        handler = _create_handler(tag)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        _loggers[name] = (logger, handler, tag)

    return logger
