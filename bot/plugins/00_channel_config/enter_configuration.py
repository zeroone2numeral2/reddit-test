import logging

import peewee
from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import Filters
from telegram.ext import ConversationHandler

from bot import mainbot
from bot.conversation import Status
from bot.plugins.commands import Command
from bot.customfilters import CustomFilters
from database.models import Channel
from bot.markups import Keyboard
from .channel_configuration.info import channelconfig_on_info_command
from .channel_configuration.remove import channelconfig_on_remove_command
from .channel_configuration.remove import channelconfig_on_confirm_delete_callbackquery
from .channel_configuration.update_pinned_message import channelconfig_on_updatepin_command
from .channel_configuration.update_title import channelconfig_on_updatetitle_command
from .channel_configuration.get_admins_and_permissions import channelconfig_on_getadmins_command
from .channel_configuration.export_invite_link import channelconfig_on_exportlink_command
from .channel_configuration.export_invite_link import channelconfig_on_linkkeep_callbackquery
from .channel_configuration.export_invite_link import channelconfig_on_linkrevoke_callbackquery
from .channel_configuration.unlink_subs import channelconfig_on_unlinksubs_command
from .channel_configuration.avgdaily import channelconfig_on_avgdaily_command
from .channel_configuration.seticon import channelconfig_on_seticon_command
from .channel_configuration.subreddits_list import channelconfig_on_subs_command
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

CHANNEL_SELECTED_TEXT = """Now you can configure {c.title}.
You can use the following commands: /unlinksubs, /remove, /avgdaily, /updatepin, /updatepic, /exportlink, /updatechat, \
/getadmins, /subs

Use /exit to exit the configuration, or /channel to change the channel to configure"""


@d.restricted
@d.failwithmessage
@d.logconversation
def on_channel_command(update: Update, context: CallbackContext):
    logger.debug('/channel: selecting channel, text: %s', update.message.text)

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    if len(context.args) > 0:
        channel_title_filter = context.args[0].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return Status.WAITING_CHANNEL_SELECTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_exit_command(update: Update, context: CallbackContext):
    logger.info('/exit command')

    context.user_data.pop('data', None)

    update.message.reply_html('Exited configuration', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel_command(update: Update, context: CallbackContext):
    logger.info('/cancel command')

    if context.user_data.get('data', None) and context.user_data['data'].get('channel', None):
        text = 'Operation canceled, back to channel configuration'
        step_to_return = Status.WAITING_CHANNEL_CONFIG_ACTION
    else:
        # it might be that the user uses /channel and then /cancel before selecting one. If we weren't already
        # inside a conversation, we should answer in a different way
        text = 'Operation canceled'
        step_to_return = ConversationHandler.END

    update.message.reply_html(text, reply_markup=Keyboard.REMOVE)

    return step_to_return


@d.restricted
@d.failwithmessage
@d.logconversation
def on_fake_cancel_command(update: Update, context: CallbackContext):
    logger.info('fake /cancel command')

    update.message.reply_html(
        'There is no operation to be canceled. Use /exit to exit the configuration mode',
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_timeout(update: Update, context: CallbackContext):
    logger.debug('conversation timeout')

    context.user_data.pop('data', None)

    update.message.reply_text('Timeout: exited styles configuration', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('/channel command: channel selected (%s)', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)

    try:
        channel = Channel.get(Channel.channel_id == channel_id)
    except peewee.DoesNotExist:
        update.message.reply_text('No channel found for "{}", try again or /cancel'.format(update.message.text))
        return Status.WAITING_CHANNEL_SELECTION

    context.user_data['data'] = dict()
    context.user_data['data']['channel'] = channel

    text = CHANNEL_SELECTED_TEXT.format(c=channel)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_waiting_channel_config_action_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_CHANNEL_CONFIG_ACTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Use /exit to exit the channel configuration mode",
        # reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_waiting_channel_selection_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_CHANNEL_SELECTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a channel or use /cancel to cancel the operation"
    )

    return Status.WAITING_CHANNEL_SELECTION


mainbot.add_handler(ConversationHandler(
    entry_points=[
        CommandHandler(['ch', 'channel'], on_channel_command)
    ],
    states={
        Status.WAITING_CHANNEL_SELECTION: [
            MessageHandler(Filters.text & ~Filters.command, on_channel_selected),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_waiting_channel_selection_unknown_message),
        ],
        Status.WAITING_CHANNEL_CONFIG_ACTION: [
            CommandHandler(['ch', 'channel'], on_channel_command),
            CommandHandler(['info'], channelconfig_on_info_command),
            CommandHandler(['remove', 'rem'], channelconfig_on_remove_command),
            CallbackQueryHandler(channelconfig_on_confirm_delete_callbackquery, pattern=r"delchannel:(.*)"),
            CommandHandler('updatepin', channelconfig_on_updatepin_command),
            CommandHandler(['updatechat', 'updatetitle'], channelconfig_on_updatetitle_command),
            CommandHandler('getadmins', channelconfig_on_getadmins_command),
            CommandHandler('exportlink', channelconfig_on_exportlink_command),
            CallbackQueryHandler(channelconfig_on_linkkeep_callbackquery, pattern=r'linkkeep'),
            CallbackQueryHandler(channelconfig_on_linkrevoke_callbackquery, pattern=r'linkrevoke'),
            CommandHandler('unlinksubs', channelconfig_on_unlinksubs_command),
            CommandHandler('avgdaily', channelconfig_on_avgdaily_command),
            CommandHandler(['updatepic', 'updateicon', 'seticon'], channelconfig_on_seticon_command),
            CommandHandler(['subs', 'subreddits'], channelconfig_on_subs_command),

            CommandHandler(Command.CANCEL, on_fake_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_waiting_channel_config_action_unknown_message),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)],
    },
    fallbacks=[CommandHandler(Command.EXIT, on_exit_command)],
    conversation_timeout=15 * 60
))
