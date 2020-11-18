import logging

from telegram.ext import CommandHandler, CallbackContext
from telegram.error import BadRequest
from telegram.error import TelegramError

from bot import mainbot
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_updatechannels_command(update, context: CallbackContext):
    logger.info('/updatechannels command')

    channels = Channel.get_all()
    if not channels:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return

    update.message.reply_text('Updating all channels...')
    errors = list()
    updated_channels = 0
    for channel in channels:
        try:
            chat = context.bot.get_chat(channel.channel_id)
        except (TelegramError, BadRequest) as e:
            logger.warning('error while getting the chat: %s', e.message)
            errors.append((channel.title, e.message))
            continue

        edited = False
        if channel.title != chat.title:
            channel.title = chat.title
            edited = True
        if channel.username != chat.username:
            channel.username = chat.username
            edited = True
        if channel.invite_link != chat.invite_link:
            channel.invite_link = chat.invite_link
            edited = True

        if edited:
            channel.save()
            updated_channels += 1

    errors_string = '\n'.join(['{}: {}'.format(title, err) for title, err in errors])
    update.message.reply_text('Channels updated: {}/{}\nErrors:\n{}'.format(updated_channels, len(channels), errors_string))


mainbot.add_handler(CommandHandler(['updatechannels'], on_updatechannels_command))
