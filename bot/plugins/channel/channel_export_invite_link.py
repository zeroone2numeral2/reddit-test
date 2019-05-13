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

from bot.markups import Keyboard
from database.models import Channel
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)


@d.restricted
@d.failwithmessage
def on_exportlink_command(_, update):
    logger.info('/exportlink command')

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_export_channel_selected(bot: Bot, update):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    try:
        invite_link = bot.export_chat_invite_link(channel_id)
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        update.message.reply_text('Error while exporting invite link: {}'.format(e.message))
        return ConversationHandler.END

    channel.invite_link = invite_link
    channel.save()

    update.message.reply_text('Invite link saved: {}'.format(invite_link), reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_export_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_export_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted')

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def exportlink_channel_conv_hanlder():

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(command=['exportlink'], callback=on_exportlink_command)],
        states={
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_export_channel_selected),
                MessageHandler(~Filters.command & Filters.all, callback=on_export_channel_selected_incorrect),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_export_cancel)
        ]
    )

    return conv_handler
