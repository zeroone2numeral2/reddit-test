import logging

# noinspection PyPackageRequirements
from telegram import Update, ChatMember, Bot, Chat
from telegram.ext import ConversationHandler
from telegram.ext import CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


def save_or_update_channel(bot: Bot, channel: Chat) -> str:
    try:
        invite_link = bot.export_chat_invite_link(channel.id)
        channel.invite_link = invite_link
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        if channel.username:
            channel.invite_link = 'https://t.me/{}'.format(channel.username)
        else:
            channel.invite_link = None

    if Channel.exists(channel.id):
        Channel.update_channel(channel)
        return 'This channel was already saved (its infos has been updated). Operation completed'
    else:
        Channel.create_from_chat(channel)
        return 'Channel {} ({}) has been saved'.format(channel.title, channel.id)


@d.restricted
@d.failwithmessage
def on_addchannel_command(update: Update, context: CallbackContext):
    logger.info('/addchannel command, args: %s', context.args)

    if not context.args:
        logger.info('no username passed')
        update.message.reply_text('Forward me a message from the channel you want to add, or /cancel')

        return Status.WAITING_FORWARDED_MESSAGE

    username = context.args[0].replace('@', '')
    logger.info('username: @%s', username)

    try:
        chat_member: ChatMember = context.bot.get_chat_member('@' + username, context.bot.id)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Add me to the channel as administrators first. Try again or /cancel ({})'.format(e.message))
        return ConversationHandler.END

    if chat_member.status != 'administrator':
        update.message.reply_text('I am not administrator of this channel, try again or /cancel')
        return ConversationHandler.END

    channel = context.bot.get_chat('@' + username)

    text = save_or_update_channel(context.bot, channel)
    update.message.reply_text(text)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_forwarded_message(update, context: CallbackContext):
    logger.info('adding channel: forwarded message OK')

    if not update.message.forward_from_chat:
        update.message.reply_text("Forward me a message from a channel (or /cancel). I'm waiting.")
        return Status.WAITING_FORWARDED_MESSAGE

    try:
        chat_member = update.message.forward_from_chat.get_member(context.bot.id)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Add me to the channel as administrators first. Try again or /cancel ({})'.format(e.message))
        return Status.WAITING_FORWARDED_MESSAGE

    if chat_member.status != 'administrator':
        update.message.reply_text('I am not administrator of this channel, try again or /cancel')
        return Status.WAITING_FORWARDED_MESSAGE

    channel = update.message.forward_from_chat

    text = save_or_update_channel(context.bot, channel)
    update.message.reply_text(text)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_non_forwarded_message(update, _):
    logger.info('adding channel: forwarded message NOT OK: not forwarded')
    update.message.reply_text('I need a forwarded message, try again or /cancel')

    return Status.WAITING_FORWARDED_MESSAGE


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['addchannel'], callback=on_addchannel_command)],
    states={
        Status.WAITING_FORWARDED_MESSAGE: [
            MessageHandler(Filters.forwarded & ~Filters.command, callback=on_forwarded_message),
            MessageHandler(~Filters.forwarded & ~Filters.command, callback=on_non_forwarded_message),
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
