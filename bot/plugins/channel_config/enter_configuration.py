import logging
import re

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
from .channel_configuration.index_channel import channelconfig_on_unposted_command
from .channel_configuration.index_channel import channelconfig_on_private_command
from .channel_configuration.index_channel import channelconfig_on_public_command
from .channel_configuration.disable import channelconfig_on_enable_command
from .channel_configuration.disable import channelconfig_on_disable_command
from .channel_configuration.postmsg import channelconfig_on_postmsg_command
from .channel_configuration.style import channelconfig_on_style_command
from .channel_configuration.style import channelconfig_on_style_selected
from .channel_configuration.style import channelconfig_waiting_style_unknown_message
from .channel_configuration.subs_property import channelconfig_on_sproperty_command
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

HELP_TEXT = """<b>Available commands</b>
/info: see the channel db row
/enable or /disable: enable/disable the channel
/unlinksubs: unlink the channel's subreddits from the channel
/remove: remove the channel from teh database, will not delete the linked subreddits
/avgdaily: number of average daily posts in the channel
/updatepin: update the channel pinned message
/updatepic: update the channel icon, using the icon of the first sub with one set
/exportlink: export and save the channel invite link
/updatechat: update the channel data
/getadmins: see the admins list and the bot permissions
/postmsg <code>[text]</code>: post a message in the channel (link preview disabled) 
/subs: list linked subreddits
/public or /private: post/don't post the channel in the index channel
/unposted: mark the channel as not posted in the index channel
/style: select a style for all the channel's subreddits
/sproperty <code>[property]</code>: show the value of that property for every subreddit of the channel

Use /exit to exit the configuration, or /channel to change the channel to configure"""

CHANNEL_SELECTED_TEXT = """Now you can configure "{c.title}"
- <a href="{c.link}">link</a>
- ID: {c.channel_id}

Use /help to see the available commands/actions

Use /exit to exit the configuration, or /channel to change the channel to configure"""


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_channel_command(update: Update, context: CallbackContext):
    logger.debug('/channel: selecting channel, text: %s', update.message.text)

    title_filter = context.args[0] if context.args else None
    channels_list: [Channel] = Channel.get_list_2(title_filter=title_filter)
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    context.user_data["__list_selection"] = []

    buttons_list = []
    for channel in channels_list:
        channel_id = str(channel.channel_id).replace('-100', '')
        buttons_list.append('{}. {}'.format(channel_id, channel.title))

        context.user_data["__list_selection"].append(channel_id)  # also happend the formatted id here

    reply_markup = Keyboard.from_list(buttons_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return Status.WAITING_CHANNEL_SELECTION


@d.restricted
@d.failwithmessage
@d.logconversation(stop_propagation=True)
@d.pass_channel
def channelconfig_on_help_command(update: Update, _, channel: Channel):
    logger.info('/help command')

    update.message.reply_html(HELP_TEXT, disable_web_page_preview=True)

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def on_exit_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/exit command')

    context.user_data.pop('data', None)

    update.message.reply_html(
        'Exited configuration mode for channel "{}"'.format(channel.title),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation()
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
@d.logconversation()
def on_fake_cancel_command(update: Update, context: CallbackContext):
    logger.info('fake /cancel command')

    update.message.reply_html(
        'There is no operation to be canceled. Use /exit to exit the configuration mode',
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def on_timeout(update: Update, context: CallbackContext, channel: Channel):
    logger.debug('conversation timeout')

    context.user_data.pop('data', None)

    update.message.reply_text('Timeout: exited {} configuration'.format(channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('/channel command: channel selected (%s)', update.message.text)

    channel_key = int(re.search(r'^(\d+).*', update.message.text, re.I).group(1))
    logger.info('channel_id: %d', channel_key)

    _, matches = u.id_match_from_list(channel_key, context.user_data["__list_selection"])
    if not matches:
        update.message.reply_text("No match for <{}>, pick another subreddit".format(channel_key))
        return Status.WAITING_CHANNEL_SELECTION
    elif len(matches) > 1:
        update.message.reply_text("Multiple matches for <{}>, pick another one".format(channel_key))
        return Status.WAITING_CHANNEL_SELECTION

    logger.debug("matches: %s", matches)

    # we have to expand it to add the -100
    channel_id = u.expand_channel_id(matches[0])

    try:
        channel = Channel.get(Channel.channel_id == channel_id)
    except peewee.DoesNotExist:
        update.message.reply_text('No channel found for "{}", try again or /cancel'.format(update.message.text))
        return Status.WAITING_CHANNEL_SELECTION

    # remove the temporary key
    context.user_data.pop("__list_selection", None)

    context.user_data['data'] = dict()
    context.user_data['data']['channel'] = channel

    text = CHANNEL_SELECTED_TEXT.format(c=channel)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_waiting_channel_config_action_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_CHANNEL_CONFIG_ACTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Use /exit to exit the channel configuration mode",
        # reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_waiting_channel_selection_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_CHANNEL_SELECTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a channel or use /cancel to cancel the operation"
    )

    return Status.WAITING_CHANNEL_SELECTION


mainbot.add_handler(ConversationHandler(
    name="channel_config",
    entry_points=[
        CommandHandler(['ch', 'channel'], on_channel_command, filters=~CustomFilters.ongoing_conversation)
    ],
    states={
        Status.WAITING_CHANNEL_SELECTION: [
            MessageHandler(Filters.text & ~Filters.command, on_channel_selected),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_waiting_channel_selection_unknown_message),
        ],
        Status.WAITING_CHANNEL_CONFIG_ACTION: [
            CommandHandler(['ch', 'channel'], on_channel_command),
            CommandHandler(['help'], channelconfig_on_help_command),
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
            CommandHandler(['private'], channelconfig_on_private_command),
            CommandHandler(['public'], channelconfig_on_public_command),
            CommandHandler(['unposted'], channelconfig_on_unposted_command),
            CommandHandler(['postmsg'], channelconfig_on_postmsg_command),
            CommandHandler(['style'], channelconfig_on_style_command),
            CommandHandler(['enable'], channelconfig_on_enable_command),
            CommandHandler(['sproperty', 'prop'], channelconfig_on_sproperty_command),
            CommandHandler(['disable'], channelconfig_on_disable_command),

            CommandHandler(Command.CANCEL, on_fake_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_waiting_channel_config_action_unknown_message),
        ],
        Status.CHANNEL_WAITING_STYLE: [
            MessageHandler(Filters.text & ~Filters.command, channelconfig_on_style_selected),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), channelconfig_waiting_style_unknown_message),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)],
    },
    fallbacks=[CommandHandler(Command.EXIT, on_exit_command)],
    conversation_timeout=15 * 60
), group=-1)
