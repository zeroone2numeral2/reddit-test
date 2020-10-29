import json
from logging.handlers import RotatingFileHandler
import logging.config
import os
import pytz
import datetime

from config import config


class TIMEZONE:
    europe_rome = pytz.timezone('Europe/Rome')


def load_logging_config(config_file='logging.json', set_rome_timezone=bool(config.get('europe_rome_timezone', True))):
    with open(config_file, 'r') as f:
        logging_config = json.load(f)

    logging.config.dictConfig(logging_config)

    def custom_timezone_converter(*args):
        utc_dt = pytz.utc.localize(datetime.datetime.utcnow())
        converted = utc_dt.astimezone(TIMEZONE.europe_rome)
        return converted.timetuple()

    if set_rome_timezone:
        logging.Formatter.converter = custom_timezone_converter

    return logging_config


logging_config = load_logging_config()


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
        self._formatter_name = 'subreddit'
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
        file_handler.setFormatter(logging.Formatter(logging_config['formatters'][self._formatter_name]['format']))
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


class SubredditLogNoAdapter(logging.Logger):
    def __init__(self, subreddit=None, dir_path='logs/subreddits/'):
        super(SubredditLogNoAdapter, self).__init__('subreddit')

        # NOT NEEDED ANYMORE
        # WE ADD BOTH THE FILE AND STREAM HANDLER MANUALLY LATER, AND ONLY TAKE
        # THE FORMATTER AND LOGGING LEVEL FROM logging.json
        # copy the logging.json's logger handlers (one SreamHandler) to this logger
        # self.handlers = logging.getLogger('subreddit').handlers

        self.subreddit_name = None
        self.subreddit_id = None
        self._dir_path = dir_path
        self._file_path = None
        self._formatter_name = 'subreddit'
        self._extra = dict()
        self._generic_logger = logging.getLogger(__name__)

        self._rotating_file_handler_kwargs = dict(
            maxBytes=1048576,
            backupCount=20,
            encoding="utf8"
        )

        self.add_handler(self.get_console_handler())

        if subreddit:
            self.set_subreddit(subreddit)

    def remove_handlers(self, file_handlers_only=False):
        for handler in self.handlers:
            if not file_handlers_only or isinstance(handler, (logging.handlers.RotatingFileHandler, logging.FileHandler)):
                self.removeHandler(handler)
                self._generic_logger.debug('removed handler %s', handler)

    def add_handler(self, handler):
        self.addHandler(handler)
        self._generic_logger.debug('added handler to Logger: %s', handler)

    def get_file_handler(self):
        handler = logging.handlers.RotatingFileHandler(
            filename=self._file_path,
            **self._rotating_file_handler_kwargs
        )
        handler.setFormatter(logging.Formatter(logging_config['formatters'][self._formatter_name]['format']))
        handler.setLevel(logging_config['loggers']['subreddit']['level'])

        return handler

    def get_console_handler(self):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging_config['formatters'][self._formatter_name]['format']))
        handler.setLevel(logging_config['loggers']['subreddit']['level'])

        return handler

    def set_subreddit(self, subreddit):
        self._generic_logger.debug('setting subreddit: %s', subreddit.name)

        self.subreddit_id = subreddit.id
        self.subreddit_name = subreddit.name
        self._dir_path = os.path.join(self._dir_path, '{}_{}'.format(subreddit.name, subreddit.id))
        self._ensure_dir(self._dir_path)
        self._file_path = os.path.join(self._dir_path, '{s.subreddit_name}_{s.subreddit_id}.log'.format(s=self))

        self._extra = {'sub_id': subreddit.id, 'sub_name': subreddit.name}

        # remove every file handler, because we are going to add a new one
        self.remove_handlers(file_handlers_only=True)

        self.add_handler(self.get_file_handler())

        return self  # return it, just in case

    def _log(self, *args, **kwargs):
        if self._extra:
            kwargs["extra"] = self._extra

        super()._log(*args, **kwargs)  # noqa

    @staticmethod
    def _ensure_dir(dir_path):
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)


slogger = SubredditLogNoAdapter()
