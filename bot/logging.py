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


class SubredditLog:
    def __init__(self, dir_path='logs/subreddits/'):
        self.subreddit_name = None
        self.subreddit_id = None
        self._dir_path = dir_path
        self._file_path = None
        self._extra = None
        self._logger: [logging.Logger, logging.LoggerAdapter] = logging.getLogger('subreddit')
        self._generic_logger = logging.getLogger(__name__)

        self._rotating_file_handler_kwargs = dict(
            maxBytes=1048576,
            backupCount=20,
            encoding="utf8"
        )

    @property
    def logger(self):
        return self._logger

    def remove_file_handlers(self):
        if not self._logger:
            return

        if isinstance(self._logger, logging.LoggerAdapter):
            for handler in self._logger.logger.handlers:
                if isinstance(handler, (logging.handlers.RotatingFileHandler, logging.FileHandler)):
                    self._logger.logger.removeHandler(handler)
                    self._generic_logger.debug('removed handler %s', handler)
        else:
            for handler in self._logger.handlers:
                if isinstance(handler, (logging.handlers.RotatingFileHandler, logging.FileHandler)):
                    self._logger.removeHandler(handler)
                    self._generic_logger.debug('removed handler %s', handler)

    def add_handler(self, handler):
        if isinstance(self._logger, logging.LoggerAdapter):
            self._logger.logger.addHandler(handler)
            self._logger = logging.LoggerAdapter(self._logger.logger, self._extra)  # remember to set the Adapter's extras
            self._generic_logger.debug('added handler to LoggerAdapter.logger %s', handler)
        elif isinstance(self._logger, logging.Logger):
            self._logger.addHandler(handler)
            self._logger = logging.LoggerAdapter(self._logger, self._extra)
            self._generic_logger.debug('added handler to Logger %s', handler)

    def set_subreddit(self, subreddit):
        self._generic_logger.debug('setting subreddit: %s', subreddit.name)

        self.subreddit_id = subreddit.id
        self.subreddit_name = subreddit.name
        self._file_path = os.path.join(self._dir_path, '{s.subreddit_name}_{s.subreddit_id}.log'.format(s=self))
        self._extra = {'sub_id': subreddit.id, 'sub_name': subreddit.name}

        self._generic_logger.debug('extra: %s', self._extra)

        if not self._logger:
            self._logger = logging.getLogger('subreddit')

        # remove every file handler, because we are going to add a new one
        self.remove_file_handlers()

        file_handler = logging.handlers.RotatingFileHandler(
            filename=self._file_path,
            **self._rotating_file_handler_kwargs
        )
        file_handler.setFormatter(logging.Formatter(logging_config['formatters']['subreddit']['format']))
        file_handler.setLevel(logging_config['loggers']['subreddit']['level'])

        self.add_handler(file_handler)

        return self._logger  # return it, just in case

    def debug(self, *args, **kwargs):
        return self._logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        return self._logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return self._logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        return self._logger.warning(*args, **kwargs)


slogger = SubredditLog()
