import logging

from telegram import Bot
from telegram.ext import CommandHandler
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Plugins

from database.models import Channel
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['updatetitles', 'titles'])
@d.restricted
@d.failwithmessage
def on_updatetitles_command(bot: Bot, update):
    logger.info('/titles command')

    channels = Channel.get_all()
    if not channels:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return

    update.message.reply_text('Updating all channels titles...')
    errors = list()
    updated_channels = 0
    for channel in channels:
        try:
            chat = bot.get_chat(channel.channel_id)
        except (TelegramError, BadRequest) as e:
            logger.warning('error while getting the chat: %s', e.message)
            errors.append((channel.title, e.message))
            continue

        if channel.title != chat.title:
            channel.title = chat.title
            channel.save()
            updated_channels += 1

    errors_string = '\n'.join(['{}: {}'.format(title, err) for title, err in errors])
    update.message.reply_text('Channels updated: {}/{}\nErrors:\n{}'.format(updated_channels, len(channels), errors_string))
