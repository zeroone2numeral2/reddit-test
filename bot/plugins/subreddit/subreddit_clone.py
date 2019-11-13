import logging
import re

from telegram.ext import ConversationHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from bot.markups import Keyboard
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

WAITING_ORIGIN_SUBREDDIT = 0

CLONE_KEYS_TO_IGNORE = (
    'subreddit_id',
    'name',
    'channel',
    'last_posted_submission_dt',
    'added',
    'id',
    'is_multireddit',
    'multireddit_owner'
)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_clonefrom_command(_, update, args=None, **kwargs):
    logger.info('/clonefrom command, args: %s', str(args))

    # we consider the second argument as a filter for the destination subreddit selection keyboard
    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit to clone the settings from, or /cancel:', reply_markup=reply_markup)

    return WAITING_ORIGIN_SUBREDDIT


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_origin_subreddit_selected(_, update, subreddit=None):
    logger.info('/clonefrom command: origin subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)
    origin_sub = Subreddit.get(Subreddit.id == subreddit_key)

    origin_dict = u.model_dict(origin_sub, plain_formatted_string=False)
    for key in CLONE_KEYS_TO_IGNORE:
        # we don't have to override these fields
        origin_dict.pop(key, None)

    logger.debug('cloning r/%s to r/%s...', origin_sub.name, subreddit.name)
    Subreddit.update(**origin_dict).where(Subreddit.id == subreddit.id).execute()

    update.message.reply_text('/r/{} settings cloned to /r/{}'.format(origin_sub.name, subreddit.name), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Okay, operation canceled', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def clone_subreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=['clonefrom'], callback=on_clonefrom_command, pass_args=True)],
        states={
            WAITING_ORIGIN_SUBREDDIT: [
                MessageHandler(Filters.text, callback=on_origin_subreddit_selected)
            ]
        },
        fallbacks=[
            CommandHandler(['cancel', 'done'], on_cancel)
        ]
    )

    return conv_handler
