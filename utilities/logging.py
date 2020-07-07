import os
import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import datetime
import pytz

from config import config


class LoggingConfig:
    dict = dict()


ROTATING_FILE_HANDLER_KWARGS = {
    "encoding": "utf8",
    "maxBytes": 1048576,
    "backupCount": 500
}


def load_logging_config(file_path):
    with open(file_path, 'r') as f:
        logging_config = json.load(f)

    LoggingConfig.dict = logging_config

    logging.config.dictConfig(logging_config)

    def custom_time(*args):
        utc_dt = pytz.utc.localize(datetime.datetime.utcnow())
        my_tz = pytz.timezone(config.get('time_zone', 'Europe/Rome'))
        converted = utc_dt.astimezone(my_tz)
        return converted.timetuple()

    logging.Formatter.converter = custom_time


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

