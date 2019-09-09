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

ORIGIN_SUBREDDIT_SELECT, DEST_SUBREDDIT_SELECT = range(2)


@d.restricted
@d.failwithmessage
def on_clone_command(_, update, args, user_data):
    logger.info('/clone command, args: %s', str(args))

    name_filter = args[0] if args else None
    if len(args) > 1:
        # we consider the second argument as a filter for the destination subreddit selection keyboard
        user_data['filter_dest'] = args[1]

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the origin subreddit, or /cancel:', reply_markup=reply_markup)

    return ORIGIN_SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
def on_origin_subreddit_selected(_, update, user_data):
    logger.info('/clone command: origin subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)
    origin_sub = Subreddit.get(Subreddit.id == subreddit_key)

    user_data['origin'] = origin_sub

    filter_dest = user_data.pop('filter_dest', None)

    subreddits = Subreddit.get_list(name_filter=filter_dest)
    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the destination subreddit (filter used: {}), or /cancel:'.format(filter_dest),
                              reply_markup=reply_markup)

    return DEST_SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
def on_dest_subreddit_selected(_, update, user_data):
    logger.info('/clone command: dest subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)
    dest_sub = Subreddit.get(Subreddit.id == subreddit_key)

    origin_sub = user_data.pop('origin')

    origin_dict = u.model_dict(origin_sub, plain_formatted_string=False)
    for key in ('subreddit_id', 'name', 'channel', 'last_posted_submission_dt', 'added', 'id'):
        # we don't have to override these fields
        origin_dict.pop(key, None)

    Subreddit.update(**origin_dict).where(Subreddit.id == dest_sub.id).execute()

    update.message.reply_text('"{}" settings cloned to "{}"'.format(origin_sub.name, dest_sub.name), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted/completed', reply_markup=Keyboard.REMOVE)

    user_data.pop('origin', None)
    user_data.pop('filter_dest', None)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def clone_subreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=['clone'], callback=on_clone_command, pass_args=True, pass_user_data=True)],
        states={
            ORIGIN_SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=on_origin_subreddit_selected, pass_user_data=True)
            ],
            DEST_SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=on_dest_subreddit_selected, pass_user_data=True)
            ]
        },
        fallbacks=[
            CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)
        ]
    )

    return conv_handler
