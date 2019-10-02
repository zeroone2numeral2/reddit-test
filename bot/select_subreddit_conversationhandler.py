import re
from functools import wraps

from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler

from bot.markups import Keyboard
from database.models import Subreddit
from utilities import d

SUBREDDIT_SELECT = range(1)


@d.restricted
@d.failwithmessage
def subreddit_selection(_, update, args):
    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    return SUBREDDIT_SELECT


class SelectSubredditConversationHandler(ConversationHandler):
    def __init__(self, entry_command, states, fallbacks, entry_points=None, *args, **kwargs):
        entry_command_hanlder = CommandHandler(command=entry_command, callback=subreddit_selection, pass_args=True)

        if entry_points:
            entry_points.insert(0, entry_command_hanlder)
        else:
            entry_points = [entry_command_hanlder]

        super().__init__(entry_points, states, fallbacks, *args, **kwargs)

    @staticmethod
    def pass_subreddit(func):
        @wraps(func)
        def wrapped(bot, update, *args, **kwargs):
            subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))

            subreddit = Subreddit.get(Subreddit.id == subreddit_key)

            return func(bot, update, subreddit, *args, **kwargs)

        return wrapped
