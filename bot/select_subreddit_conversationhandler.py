import re
import logging
from functools import wraps

from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler

from bot.markups import Keyboard
from database.models import Subreddit
from utilities import d

logger = logging.getLogger(__name__)

FIRST_STEP = 0


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.debug('shared subreddit selector (fallback), text: %s', update.message.text)

    update.message.reply_text('Operation aborted/completed', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def subreddit_selection(_, update, args):
    logger.debug('shared subreddit selector (entry point), text: %s', update.message.text)

    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    logger.debug('returing next state: %d', FIRST_STEP)
    return FIRST_STEP  # first step after the entry point


class SelectSubredditConversationHandler(ConversationHandler):
    def __init__(self, entry_command, states, fallbacks=None, entry_points=None, *args, **kwargs):
        entry_command_hanlder = CommandHandler(command=entry_command, callback=subreddit_selection, pass_args=True)

        if entry_points:
            entry_points.insert(0, entry_command_hanlder)
        else:
            entry_points = [entry_command_hanlder]

        if not fallbacks:
            fallbacks = [CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)]

        # print(entry_points, states, fallbacks)

        super().__init__(entry_points, states, fallbacks, *args, **kwargs)

    @staticmethod
    def pass_subreddit(func):
        @wraps(func)
        def wrapped(bot, update, *args, **kwargs):
            subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
            logger.debug('subreddit fetcher decorator: subreddit id: %d', subreddit_key)

            subreddit = Subreddit.get(Subreddit.id == subreddit_key)

            return func(bot, update, subreddit=subreddit, *args, **kwargs)

        return wrapped
