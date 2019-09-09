import logging
import re

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from database.models import Channel
from database.models import Subreddit
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT, CHANNEL_SELECT = range(2)


@d.restricted
@d.failwithmessage
def on_set_channel_command(_, update, args):
    logger.info('/subchannel command, args: %s', args)

    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    return SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
def on_subreddit_selected(_, update, user_data):
    logger.info('subreddit selected: %s', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)

    subreddit = Subreddit.get(Subreddit.id == subreddit_key)

    user_data['subreddit'] = subreddit

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text(
        'Selected subreddit: /r/{s.name} (channel: {s.channel.title}). Select the new channel, or /cancel:'.format(s=subreddit),
        reply_markup=reply_markup
    )

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(_, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit = user_data.pop('subreddit')
    subreddit.channel = channel
    subreddit.save()

    update.message.reply_text('r/{}\'s channel saved: {}'.format(subreddit.name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel', reply_markup=Keyboard.REMOVE)

    return CHANNEL_SELECT


@Plugins.add_conversation_hanlder()
def setchannel_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(
            command=['subchannel', 'setchannel'],
            callback=on_set_channel_command,
            pass_args=True
        )],
        states={
            SUBREDDIT_SELECT: [MessageHandler(Filters.text, callback=on_subreddit_selected, pass_user_data=True)],
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_channel_selected,
                               pass_user_data=True),
                MessageHandler(~Filters.command & Filters.all, callback=on_channel_selected_incorrect),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_cancel, pass_user_data=True)
        ]
    )

    return conv_handler
