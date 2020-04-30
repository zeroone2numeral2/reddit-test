import json
from logging.handlers import RotatingFileHandler
import logging.config
import os

with open('logging.json', 'r') as f:
    logging_config = json.load(f)

logging.config.dictConfig(logging_config)


def get_subreddit_logger(subreddit, dir_path='logs/subreddits/'):
    file_path = os.path.join(dir_path, subreddit.name + '.log')

    extra = {'sub_id': subreddit.id, 'sub_name': subreddit.name}

    logger = logging.getLogger('subreddit')
    fh = logging.handlers.RotatingFileHandler(
        filename=file_path,
        maxBytes=1048576,
        backupCount=20,
        encoding="utf8"
    )
    fh.setFormatter(logging.Formatter(logging_config['formatters']['subreddit']['format']))
    fh.setLevel(logging_config['loggers']['subreddit']['level'])
    logger.addHandler(fh)

    logger = logging.LoggerAdapter(logger, extra)

    return logger




