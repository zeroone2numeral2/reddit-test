import logging

from telegram import Bot
from telegram.ext import CommandHandler
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Plugins

from database.models import Channel
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['members'])
@d.restricted
@d.failwithmessage
def on_top_members_command(bot: Bot, update):
    logger.info('/members command')

    channels = Channel.get_all()
    if not channels:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return

    update.message.reply_text('Getting the members count...')
    errors = list()
    channels_members = list()
    for channel in channels:
        try:
            channel_count = bot.getChatMembersCount(channel.channel_id)
        except (TelegramError, BadRequest) as e:
            logger.warning('error while getting the chat: %s', e.message)
            errors.append((channel.title, e.message))
            continue

        channels_members.append((channel.title, channel_count))

    channels_members.sort(key=lambda x: x[1], reverse=True)

    channels_string = '\n'.join(['{0}: {1}'.format(*c) for c in channels_members][:9])
    errors_string = '\n'.join(['{}: {}'.format(title, err) for title, err in errors])
    update.message.reply_text('{}\n\nErrors:\n{}'.format(channels_string, errors_string))
