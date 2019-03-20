import logging
from functools import wraps
from utilities import u

from config import config

logger = logging.getLogger(__name__)


def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if update.effective_user.id not in config.telegram.admins:
            if update.effective_chat.id > 0:
                # only answer in private
                update.message.reply_text("You can't use this command")
            return

        return func(bot, update, *args, **kwargs)

    return wrapped


def failwithmessage(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            return func(bot, update, *args, **kwargs)
        except Exception as e:
            logger.error('error during handler execution: %s', str(e), exc_info=True)
            text = 'An error occurred while processing the message: <code>{}</code>'.format(u.escape(str(e)))
            update.message.reply_html(text)

    return wrapped


def logerrors(func):
    @wraps(func)
    def wrapped(bot, job, *args, **kwargs):
        try:
            return func(bot, job, *args, **kwargs)
        except Exception as e:
            logger.error('error during job execution: %s', str(e), exc_info=True)

    return wrapped
