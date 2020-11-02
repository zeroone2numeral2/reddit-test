import logging

# noinspection PyPackageRequirements
from telegram.ext import ConversationHandler, CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from bot.markups import InlineKeyboard
from database.models import Channel
from .select_channel import channel_selection_handler
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


def on_link_keep_button(update, context: CallbackContext):
    logger.info('linkkeep inline button')
    update.callback_query.edit_message_text('Fine, we will keep the current invite link')

    context.user_data.pop('db_channel', None)


def on_link_revoke_button(update, context: CallbackContext):
    logger.info('linkrevoke inline button')
    update.callback_query.edit_message_text('Fine, we will keep the current invite link')

    channel = context.user_data.pop('db_channel', None)

    try:
        invite_link = context.bot.export_chat_invite_link(channel.channel_id)
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
def on_export_channel_selected(update, context: CallbackContext):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    if channel.invite_link:
        inline_markup = InlineKeyboard.row_from_list([('yes, revoke and generate a new one', 'linkrevoke'), ('no', 'linkkeep')])
        update.message.reply_text('This channel already has am invite link saved: {}'.format(channel.invite_link),
                                  disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)
        update.message.reply_text('Do you want to generate a new one?', reply_markup=inline_markup)

        context.user_data['db_channel'] = channel

        return ConversationHandler.END

    try:
        # first: try to revoke the current invite link
        invite_link = context.bot.export_chat_invite_link(channel_id)
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)

        # maybe the channel is public and the bot doesn't have the permission to generete an invite link, so we try to get the chat
        channel_object = context.bot.get_chat(channel_id)
        if channel_object.username:
            invite_link = 'https://t.me/{}'.format(channel_object.username)
        else:
            update.message.reply_text('Error while exporting invite link (the channel is not public): {}'.format(e.message))
            return ConversationHandler.END

    channel.invite_link = invite_link
    channel.save()

    update.message.reply_text('Invite link saved: {}'.format(invite_link), reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_export_channel_selected_incorrect(update, _):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return Status.CHANNEL_SELECTED


@d.restricted
@d.failwithmessage
def on_export_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(CallbackQueryHandler(on_link_keep_button, pattern=r'linkkeep', pass_user_data=True))
mainbot.add_handler(CallbackQueryHandler(on_link_revoke_button, pattern=r'linkrevoke', pass_user_data=True))
mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['exportlink'], callback=channel_selection_handler)],
    states={
        Status.CHANNEL_SELECTED: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_export_channel_selected),
            MessageHandler(~Filters.command & Filters.all, callback=on_export_channel_selected_incorrect),
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_export_cancel)
    ]
))
