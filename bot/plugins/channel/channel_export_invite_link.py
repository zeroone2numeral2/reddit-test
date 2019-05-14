import logging

# noinspection PyPackageRequirements
from telegram import Bot
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Plugins

from bot.markups import Keyboard
from bot.markups import InlineKeyboard
from database.models import Channel
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)


@Plugins.add(CallbackQueryHandler, pattern=r'linkkeep', pass_user_data=True)
def on_link_keep_button(_, update, user_data):
    logger.info('linkkeep inline button')
    update.callback_query.edit_message_text('Fine, we will keep the current invite link')

    user_data.pop('db_channel', None)


@Plugins.add(CallbackQueryHandler, pattern=r'linkrevoke', pass_user_data=True)
def on_link_revoke_button(bot, update, user_data):
    logger.info('linkrevoke inline button')
    update.callback_query.edit_message_text('Fine, we will keep the current invite link')

    channel = user_data.pop('db_channel', None)

    try:
        invite_link = bot.export_chat_invite_link(channel.channel_id)
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        update.callback_query.edit_message_text('Error while exporting invite link: {}'.format(e.message))
        return

    channel.invite_link = invite_link
    channel.save()

    update.callback_query.edit_message_text(
        'New invite link saved: {}'.format(invite_link),
        reply_markup=InlineKeyboard.REMOVE,
        disable_web_page_preview=True
    )


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
def on_export_channel_selected(bot: Bot, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    if channel.invite_link:
        inline_markup = InlineKeyboard.row_from_list([('yes, revoke and generate a new one', 'linkrevoke'), ('no', 'linkkeep')])
        update.message.reply_text('This channel already has am invite link saved: {}'.format(channel.invite_link),
                                  disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)
        update.message.reply_text('Do you want to generate a new one?', reply_markup=inline_markup)

        user_data['db_channel'] = channel

        return ConversationHandler.END

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
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_export_channel_selected,
                               pass_user_data=True),
                MessageHandler(~Filters.command & Filters.all, callback=on_export_channel_selected_incorrect),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_export_cancel)
        ]
    )

    return conv_handler
