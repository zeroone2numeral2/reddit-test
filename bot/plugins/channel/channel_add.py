import logging

# noinspection PyPackageRequirements
from telegram.ext import ConversationHandler
from telegram.ext import CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError

from bot import mainbot
from bot.markups import Keyboard
from database.models import Channel
from utilities import d

logger = logging.getLogger(__name__)

FORWARD_MESSAGE = range(1)


@d.restricted
@d.failwithmessage
def on_addchannel_command(update, _):
    logger.info('/addchannel command')

    update.message.reply_text('Forward me a message from the channel you want to add, or /cancel')

    return FORWARD_MESSAGE


@d.restricted
@d.failwithmessage
def on_forwarded_message(update, context: CallbackContext):
    logger.info('adding channel: forwarded message OK')

    if not update.message.forward_from_chat:
        update.message.reply_text("Forward me a message from a channel (or /cancel). I'm waiting.")
        return FORWARD_MESSAGE

    try:
        chat_member = update.message.forward_from_chat.get_member(context.bot.id)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Add me to the channel as administrators first. Try again or /cancel ({})'.format(e.message))
        return FORWARD_MESSAGE

    if chat_member.status != 'administrator':
        update.message.reply_text('I am not administrator of this channel, try again or /cancel')
        return FORWARD_MESSAGE

    channel = update.message.forward_from_chat

    try:
        invite_link = context.bot.export_chat_invite_link(channel.id)
        channel.invite_link = invite_link
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        if channel.username:
            channel.invite_link = 'https://t.me/{}'.format(channel.username)
        else:
            channel.invite_link = None

    if Channel.exists(channel.id):
        Channel.update_channel(channel)
        update.message.reply_text('This channel was already saved (its infos has been updated). Operation completed')
    else:
        Channel.create_from_chat(channel)
        update.message.reply_text('Channel {} ({}) has been saved'.format(channel.title, channel.id))

    if channel.invite_link:
        update.message.reply_text('Exported invite link/public link: {}'.format(channel.invite_link), disable_web_page_preview=True)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_non_forwarded_message(update, _):
    logger.info('adding channel: forwarded message NOT OK: not forwarded')
    update.message.reply_text('I need a forwarded message, try again or /cancel')

    return FORWARD_MESSAGE


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['addchannel'], callback=on_addchannel_command)],
    states={
        FORWARD_MESSAGE: [
            MessageHandler(Filters.forwarded & ~Filters.command, callback=on_forwarded_message),
            MessageHandler(~Filters.forwarded & ~Filters.command, callback=on_non_forwarded_message),
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
