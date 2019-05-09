import os
import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler


class LoggingConfig:
    dict = dict()


ROTATING_FILE_HANDLER_KWARGS = {
    "encoding": "utf8",
    "maxBytes": 1048576,
    "backupCount": 500
}


def load_logging_config(file_path, logfile):
    with open(file_path, 'r') as f:
        logging_config = json.load(f)
    logging_config['handlers']['file']['filename'] = logfile

    LoggingConfig.dict = logging_config

    logging.config.dictConfig(logging_config)


class SubredditRotatingFileHanlder(RotatingFileHandler):
    def __init__(self, sub_name, *args, **kwargs):
        file_path = os.path.join('logs', 'subreddits', sub_name + '.log')
        RotatingFileHandler.__init__(self, file_path, *args, **kwargs)


def set_logger_file(logger_name, sub_name=None):
    l = logging.getLogger(logger_name)

    file_name = '{}.log'.format(sub_name if sub_name else 'redditmirror')
    file_path = os.path.join('logs', file_name)

    rfhandler = RotatingFileHandler(file_path, maxBytes=1048576, backupCount=500)
    formatter = logging.Formatter('[%(asctime)s][%(name)s][%(pathname)s:%(filename)s:%(funcName)s:%(lineno)d][%(levelname)s] >>> %(message)s')
    rfhandler.setFormatter(formatter)
    rfhandler.setLevel(logging.DEBUG)

    l.handlers = [rfhandler]

    return l

