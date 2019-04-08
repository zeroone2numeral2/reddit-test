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


def get_subreddit_logger(sub_name):
    logger = logging.getLogger(sub_name)
    if len(logger.handlers) < 1:
        rotating_file_handler = SubredditRotatingFileHanlder(sub_name, **ROTATING_FILE_HANDLER_KWARGS)
        formatter = logging.Formatter('[%(asctime)s][%(filename)s:%(lineno)d][%(levelname)s] >>> %(message)s')
        rotating_file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(rotating_file_handler)

    return logger

