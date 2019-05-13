import logging

# noinspection PyPackageRequirements
from telegram import Bot
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Plugins

from database.models import Channel
from utilities import d

logger = logging.getLogger(__name__)

FORWARD_MESSAGE = range(1)


@d.restricted
@d.failwithmessage
def on_addchannel_command(_, update):
    logger.info('/addchannel command')

    update.message.reply_text('Forward me a message from the channel you want to add, or /cancel')

    return FORWARD_MESSAGE


@d.restricted
@d.failwithmessage
def on_forwarded_message(bot: Bot, update):
    logger.info('adding channel: forwarded message OK')

    if not update.message.forward_from_chat:
        update.message.reply_text("Forward me a message from a channel (or /cancel). I'm waiting.")
        return FORWARD_MESSAGE

    try:
        chat_member = update.message.forward_from_chat.get_member(bot.id)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Add me to the channel as administrators first. Try again or /cancel ({})'.format(e.message))
        return FORWARD_MESSAGE

    if chat_member.status != 'administrator':
        update.message.reply_text('I am not administrator of this channel, try again or /cancel')
        return FORWARD_MESSAGE

    channel = update.message.forward_from_chat

    try:
        invite_link = bot.export_chat_invite_link(channel.id)
        channel.invite_link = invite_link
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        channel.invite_link = None

    if Channel.exists(channel.id):
        Channel.update_channel(channel)
        update.message.reply_text('This channel was already saved (its infos has been updated). Operation completed')
    else:
        Channel.create_from_chat(update.message.forward_from_chat)
        update.message.reply_text('Channel {} ({}) has been saved'.format(channel.title, channel.id))

    if channel.invite_link:
        update.message.reply_text('Exported invite link: {}'.format(channel.invite_link), disable_web_page_preview=True)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_non_forwarded_message(_, update):
    logger.info('adding channel: forwarded message NOT OK: not forwarded')
    update.message.reply_text('I need a forwarded message, try again or /cancel')

    return FORWARD_MESSAGE


@d.restricted
@d.failwithmessage
def on_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted')

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def addchannel_conv_hanlder():

    conv_handler = ConversationHandler(
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
    )

    return conv_handler
