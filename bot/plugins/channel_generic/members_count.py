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
def on_top_members_command(update, context: CallbackContext):
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
            channel_count = context.bot.getChatMembersCount(channel.channel_id)
        except (TelegramError, BadRequest) as e:
            logger.warning('error while getting the chat: %s', e.message)
            errors.append((channel.title, e.message))
            continue

        channels_members.append((channel.title, channel_count))

    channels_members.sort(key=lambda x: x[1], reverse=True)

    channels_string = '\n'.join(['{i}) {0}: {1}'.format(*c, i=i+1) for i, c in enumerate(channels_members)][:24])
    errors_string = '\n'.join(['{}: {}'.format(title, err) for title, err in errors])
    update.message.reply_text('{}\n\nErrors:\n{}'.format(channels_string, errors_string))


mainbot.add_handler(CommandHandler('members', on_top_members_command))
