import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot import mainbot
from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_remchannel_command(update, _):
    logger.info('/remchannel command')

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(update, _):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if channel_subreddits:
        for subreddit in channel_subreddits:
            subreddit.channel = None
            subreddit.save()
            logger.debug('removed bind channel for subreddit r/%s', subreddit.name)

    channel_title = channel.title
    
    logger.info('Deleting channel...')
    channel.delete_instance()
    
    update.message.reply_text(
        'Channel "{}" removed. Linked subreddits: {} (if any, their channel as been set to NULL)'.format(
            channel_title,
            ', '.join([s.name for s in channel_subreddits]) if channel_subreddits else 'none'
        ),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['remchannel'], callback=on_remchannel_command)],
    states={
        CHANNEL_SELECT: [
            MessageHandler(Filters.text, callback=on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
