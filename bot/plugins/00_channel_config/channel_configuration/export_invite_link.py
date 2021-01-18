import logging

from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackContext

from bot.conversation import Status
from bot.markups import InlineKeyboard, Keyboard
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_linkkeep_callbackquery(update, context: CallbackContext, channel: Channel):
    logger.info('linkkeep inline button')
    update.callback_query.edit_message_text('Fine, we will keep the current invite link')

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_linkrevoke_callbackquery(update, context: CallbackContext, channel: Channel):
    logger.info('linkrevoke inline button')

    try:
        invite_link = context.bot.export_chat_invite_link(channel.channel_id)
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)
        update.callback_query.edit_message_text('Error while exporting invite link: {}'.format(e.message))
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel.invite_link = invite_link
    channel.save()

    update.callback_query.edit_message_text(
        'New invite link saved: {}'.format(invite_link),
        reply_markup=InlineKeyboard.REMOVE,
        disable_web_page_preview=True
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_exportlink_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/exportlink command')

    if channel.invite_link:
        inline_markup = InlineKeyboard.row_from_list([('yes, revoke and generate a new one', 'linkrevoke'), ('no', 'linkkeep')])
        update.message.reply_text('This channel already has an invite link saved: {}'.format(channel.invite_link),
                                  disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)
        update.message.reply_text('Do you want to generate a new one?', reply_markup=inline_markup)

        return Status.WAITING_CHANNEL_CONFIG_ACTION

    try:
        # first: try to revoke the current invite link
        invite_link = context.bot.export_chat_invite_link(channel.channel_id)
    except (TelegramError, BadRequest) as e:
        logger.error('error while exporting invite link: %s', e.message)

        # maybe the channel is public and the bot doesn't have the permission to generete an invite link, so we try to get the chat
        channel_object = context.bot.get_chat(channel.channel_id)
        if channel_object.username:
            invite_link = 'https://t.me/{}'.format(channel_object.username)
        else:
            update.message.reply_text('Error while exporting invite link (the channel is not public): {}'.format(e.message))
            return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel.invite_link = invite_link
    channel.save()

    update.message.reply_text('Invite link saved: {}'.format(invite_link), reply_markup=Keyboard.REMOVE,
                              disable_web_page_preview=True)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
