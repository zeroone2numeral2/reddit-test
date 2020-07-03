import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, CallbackContext
from telegram.ext import Filters
from telegram.ext import ConversationHandler

from bot import mainbot
from bot.conversation import Status
from bot.customfilters import CustomFilters
from database.models import Subreddit
from bot.markups import Keyboard
from .subreddit_configuration.dbentry import subconfig_on_entry_change
from .subreddit_configuration.info import subconfig_on_info_command
from .subreddit_configuration.disable import subconfig_on_disable_command
from .subreddit_configuration.remove import subconfig_on_remove_command
from .subreddit_configuration.settemplate import subconfig_on_settemplate_command
from .subreddit_configuration.seticon import subconfig_on_setchannelicon_command
from .subreddit_configuration.topstorage import subconfig_on_savetop_command
from .subreddit_configuration.topstorage import subconfig_on_gettop_command
from .subreddit_configuration.topstorage import subconfig_on_removetop_command
from .subreddit_configuration.channel import subconfig_on_setchannel_command
from .subreddit_configuration.channel import subconfig_on_selected_channel
from .subreddit_configuration.channel import subconfig_on_selected_channel_wrong
from .subreddit_configuration.clone import subconfig_on_clonefrom_command
from .subreddit_configuration.clone import subconfig_on_origin_subreddit_selected
from .subreddit_configuration.clone import subconfig_on_selected_subreddit_wrong
from .subreddit_configuration.clonestyle import subconfig_on_clonestylefrom_command
from .subreddit_configuration.clonestyle import subconfig_on_clonestyle_origin_subreddit_selected
from .subreddit_configuration.clonestyle import subconfig_on_clonestyle_selected_subreddit_wrong
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

ENABLED = False

TEXT = """You are configuring <a href="https://reddit.com/r/{s.name}">/r/{s.name}</a> (channel: {channel_title}, \
link: {invite_link})

<b>Available commands</b>: \
/info, \
/remove (remove the subreddit from the db), \
/setchannel (set the subreddit's channel), \
/clonefrom (override the settings of the current subreddit with those from another one), \
/clonestylefrom (override the style settings of the current subreddit with those from another one), \
/setchannelicon (use this subreddit's icon as channel icon), \
/disable (disable the subreddit), \
/savetop (save the current top posts of the subreddit, so we won't post them if the sorting is "month" or "all"), \
/removetop (remove the saved top posts for this subreddit with the current sorting), \
/gettop (see how many top posts we have saved for the current sorting), \
/settemplate (use one of the default templates for this subreddit)

You can also pass one of the subreddit's properties to see or change them, for example:
• "<code>template</code>" will show the current template
• "<code>max_frequency 295</code>" will change <code>max_frequency</code> to 295

Use /end when you are done\
"""


@d.restricted
@d.failwithmessage
@d.logconversation
def on_sub_command(update: Update, context: CallbackContext):
    logger.debug('/sub: selecting subreddit, text: %s', update.message.text)

    name_filter = context.args[0] if context.args else None

    subreddits: [Subreddit] = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    buttons_list = ['{}. /{}/{} ({})'.format(s.id, 'm' if s.is_multireddit else 'r', s.name, s.channel.title if s.channel else 'no channel') for s in subreddits]
    reply_markup = Keyboard.from_list(buttons_list)

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    return Status.SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_subreddit_selected_wrong(update: Update, _):
    logger.debug('/sub: subreddit regex failed, text: %s', update.message.text)

    update.message.reply_text('Please select a subreddit from the keyboard')

    return Status.SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_subreddit_selected(update: Update, context: CallbackContext):
    logger.info('/sub command: subreddit selected (%s)', update.message.text)

    # subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    subreddit_key = int(re.search(r'^(\d+).*', update.message.text, re.I).group(1))
    logger.debug('subreddit id: %d', subreddit_key)

    subreddit = Subreddit.get(Subreddit.id == subreddit_key)

    context.user_data['data'] = dict()
    context.user_data['data']['subreddit'] = subreddit

    channel_invite_link = u.channel_invite_link(subreddit.channel, return_on_no_link='-', hyperlink_html='here')
    text = TEXT.format(s=subreddit, channel_title=subreddit.channel_title(), invite_link=channel_invite_link)

    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit_2
def on_cancel_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    # this is used only for sub-conversations
    logger.info('/cancel command')

    for k, v in context.user_data['data'].items():
        if k.lower() != 'subreddit':
            # remove every temporary data that is NOT the subreddit object
            context.user_data['data'].pop(k)

    update.message.reply_html(
        'Operation canceled.\nBack to /r/{s.name}\'s configuration'.format(s=subreddit),
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.pass_subreddit_2
@d.logconversation
def on_end(update: Update, context: CallbackContext, subreddit=None):
    logger.debug('/end command')

    text = 'Exited configuration mode for /r/{s.name} (channel: {channel})'.format(s=subreddit, channel=subreddit.channel_title())

    context.user_data.pop('data', None)

    update.message.reply_text(text)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.pass_subreddit_2
@d.logconversation
def on_timeout(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.debug('conversation timeout')

    text = 'Timeout: exited configuration mode for /r/{s.name} (channel: {channel})'.format(s=subreddit, channel=subreddit.channel_title())

    context.user_data.pop('data', None)

    update.message.reply_text(text)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(['sub', 'subreddit'], on_sub_command)],
    states={
        Status.SUBREDDIT_SELECT: [
            MessageHandler(Filters.text & Filters.regex(r'^(\d+).*'), on_subreddit_selected),
            MessageHandler(Filters.text, on_subreddit_selected_wrong)
        ],
        Status.WAITING_SUBREDDIT_CONFIG_ACTION: [
            MessageHandler(Filters.text & CustomFilters.subreddit_set & ~Filters.command, subconfig_on_entry_change),
            CommandHandler(['info'], subconfig_on_info_command),
            CommandHandler(['disable'], subconfig_on_disable_command),
            CommandHandler(['remove', 'rem'], subconfig_on_remove_command),
            CommandHandler(['settemplate'], subconfig_on_settemplate_command),
            CommandHandler(['setchannelicon'], subconfig_on_setchannelicon_command),
            CommandHandler(['savetop'], subconfig_on_savetop_command),
            CommandHandler(['gettop', 'getop'], subconfig_on_gettop_command),
            CommandHandler(['removetop', 'remtop'], subconfig_on_removetop_command),
            CommandHandler(['setchannel'], subconfig_on_setchannel_command),
            CommandHandler(['clonefrom'], subconfig_on_clonefrom_command),
            CommandHandler(['clonestylefrom'], subconfig_on_clonestylefrom_command),
        ],
        Status.SETCHANNEL_WAITING_CHANNEL: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), subconfig_on_selected_channel),
            MessageHandler(~Filters.command & Filters.all, subconfig_on_selected_channel_wrong),
            CommandHandler(['cancel'], on_cancel_command),
        ],
        Status.CLONE_WAITING_ORIGIN_SUBREDDIT: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), subconfig_on_origin_subreddit_selected),
            MessageHandler(~Filters.command & Filters.all, subconfig_on_selected_subreddit_wrong),
            CommandHandler(['cancel'], on_cancel_command),
        ],
        Status.CLONESTYLE_WAITING_ORIGIN_SUBREDDIT: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), subconfig_on_clonestyle_origin_subreddit_selected),
            MessageHandler(~Filters.command & Filters.all, subconfig_on_clonestyle_selected_subreddit_wrong),
            CommandHandler(['cancel'], on_cancel_command),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)]
    },
    fallbacks=[CommandHandler(['end', 'exit'], on_end)],
    conversation_timeout=15 * 60
))