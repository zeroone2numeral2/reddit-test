import logging
import re

from telegram import Update, ParseMode
from telegram.ext import MessageHandler, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import Filters
from telegram.ext import ConversationHandler

from bot import mainbot
from bot.conversation import Status
from bot.plugins.commands import Command
from bot.customfilters import CustomFilters
from database.models import Subreddit
from bot.markups import Keyboard, InlineKeyboard
from .subreddit_configuration.dbentry import subconfig_on_entry_change
from .subreddit_configuration.info import subconfig_on_info_command
from .subreddit_configuration.disable import subconfig_on_disable_command
from .subreddit_configuration.remove import subconfig_on_remove_command
from .subreddit_configuration.seticon import subconfig_on_setchannelicon_command
from .subreddit_configuration.frequency import subconfig_on_freq_command
from .subreddit_configuration.topstorage import subconfig_on_savetop_command
from .subreddit_configuration.topstorage import subconfig_on_gettop_command
from .subreddit_configuration.topstorage import subconfig_on_removetop_command
from .subreddit_configuration.channel import subconfig_on_setchannel_command
from .subreddit_configuration.channel import subconfig_on_selected_channel
from .subreddit_configuration.channel import subconfig_on_selected_channel_wrong
from .subreddit_configuration.clone import subconfig_on_clonefrom_command
from .subreddit_configuration.clone import subconfig_on_origin_subreddit_selected
from .subreddit_configuration.clone import subconfig_on_selected_subreddit_wrong
from .subreddit_configuration.style import subconfig_on_getstyle_command
from .subreddit_configuration.style import subconfig_on_setstyle_command
from .subreddit_configuration.style import subconfig_on_style_selected
from .subreddit_configuration.see_submissions import subconfig_on_submissions_command
from .subreddit_configuration.daily_posts_avg import subconfig_on_avgdaily_command
from .subreddit_configuration.flairs import subconfig_on_flairs_command
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

TEXT = """You are configuring <a href="https://reddit.com/r/{s.name}">{s.r_name}</a> (channel: {s.ch_title}, \
link: {s.channel_link})

<b>Available commands</b>: \
/info, \
/remove (remove the subreddit from the db), \
/setchannel (set the subreddit's channel), \
/submissions (get the sub's frontpage based on the current sorting/limit, and see what has been already posted), \
/clonefrom (override the settings of the current subreddit with those from another one), \
/style (change this subreddit's style), \
/getstyle (see the current style), \
/dailyavg (past 7 days avg number of posts/day), \
/setchannelicon (use this subreddit's icon as channel icon), \
/disable (disable the subreddit), \
/freq (set the posting frequency), \
/flairs (see the sub's flairs), \
/savetop (save the current top posts of the subreddit, so we won't post them if the sorting is "month" or "all"), \
/removetop (remove the saved top posts for this subreddit with the current sorting), \
/gettop (see how many top posts we have saved for the current sorting)

You can also pass one of the subreddit's properties to see or change them, for example:
• "<code>template</code>" will show the current template
• "<code>max_frequency 295</code>" will change <code>max_frequency</code> to 295

Use /exit when you are done, or /sub to change subreddit\
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


@d.failwithmessage
@d.logconversation
def on_configure_inline_button(update, context: CallbackContext):
    logger.info('configure inline button')

    subreddit = Subreddit.get(id=int(context.matches[0].group(1)))

    context.user_data['data'] = dict()
    context.user_data['data']['subreddit'] = subreddit

    text = TEXT.format(s=subreddit)
    update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboard.REMOVE,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


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

    text = TEXT.format(s=subreddit)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel_command(update: Update, context: CallbackContext):
    # this is used only for sub-conversations
    logger.info('/cancel command')

    if context.user_data.get('data', None):
        keys_to_pop = []
        for k, v in context.user_data['data'].items():
            if k.lower() != 'subreddit':
                # remove every temporary data that is NOT the subreddit object
                keys_to_pop.append(k)

        for key in keys_to_pop:
            context.user_data['data'].pop(key)

    if u.get_subreddit_from_userdata(context.user_data):
        # it might be that we do not have a subreddit saved in user_data yet (for example: user uses /sub and
        # then /cancel before selecting a subreddit)
        text = 'Operation canceled.\nBack to {s.r_name}\'s configuration'.format(s=context.user_data['data']['subreddit'])
        step_to_return = Status.WAITING_SUBREDDIT_CONFIG_ACTION
    else:
        text = 'Operation canceled'
        step_to_return = ConversationHandler.END

    update.message.reply_html(
        text,
        reply_markup=Keyboard.REMOVE
    )

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

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_waiting_subreddit_config_action_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_SUBREDDIT_CONFIG_ACTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Use /exit to exit the subreddit configuration mode",
        # reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def on_subreddit_select_unknown_message(update: Update, context: CallbackContext):
    logger.info('SUBREDDIT_SELECT: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a subreddit or use /cancel"
    )

    return Status.SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_setchannel_waiting_channel_unknown_message(update: Update, context: CallbackContext):
    logger.info('SETCHANNEL_WAITING_CHANNEL: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a channel or use /cancel"
    )

    return Status.SETCHANNEL_WAITING_CHANNEL


@d.restricted
@d.failwithmessage
@d.logconversation
def on_subreddit_waiting_style_unknown_message(update: Update, context: CallbackContext):
    logger.info('SUBREDDIT_WAITING_STYLE: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a style or use /cancel"
    )

    return Status.SUBREDDIT_WAITING_STYLE


@d.restricted
@d.failwithmessage
@d.logconversation
def on_clone_waiting_origin_subreddit_unknown_message(update: Update, context: CallbackContext):
    logger.info('CLONE_WAITING_ORIGIN_SUBREDDIT: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select an origin subreddit or use /cancel"
    )

    return Status.CLONE_WAITING_ORIGIN_SUBREDDIT


@d.restricted
@d.failwithmessage
@d.pass_subreddit
@d.logconversation
def on_exit_command(update: Update, context: CallbackContext, subreddit=None):
    logger.debug('/exit command')

    text = 'Exited configuration mode for {s.r_name} (channel: {s.ch_title})'.format(s=subreddit)

    context.user_data.pop('data', None)

    update.message.reply_text(text)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.pass_subreddit
@d.logconversation
def on_timeout(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.debug('conversation timeout')

    text = 'Timeout: exited configuration mode for {s.r_name} (channel: {s.ch_title})'.format(s=subreddit)

    context.user_data.pop('data', None)

    update.message.reply_text(text, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    name="subreddit_config",
    entry_points=[
        CommandHandler(['sub', 'subreddit', 'subconfig'], on_sub_command),
        CallbackQueryHandler(on_configure_inline_button, pattern=r'configsub:(\d+)', pass_groups=True)
    ],
    states={
        Status.SUBREDDIT_SELECT: [
            MessageHandler(Filters.text & Filters.regex(r'^(\d+).*') & ~Filters.command, on_subreddit_selected),
            MessageHandler(Filters.text & ~Filters.command, on_subreddit_selected_wrong),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_subreddit_select_unknown_message),
        ],
        Status.WAITING_SUBREDDIT_CONFIG_ACTION: [
            MessageHandler(Filters.text & CustomFilters.subreddit_set & ~Filters.command, subconfig_on_entry_change),
            CommandHandler(['info'], subconfig_on_info_command),
            CommandHandler(['disable'], subconfig_on_disable_command),
            CommandHandler(['remove', 'rem'], subconfig_on_remove_command),
            CommandHandler(['freq'], subconfig_on_freq_command),
            CommandHandler(['setchannelicon'], subconfig_on_setchannelicon_command),
            CommandHandler(['savetop'], subconfig_on_savetop_command),
            CommandHandler(['gettop', 'getop'], subconfig_on_gettop_command),
            CommandHandler(['removetop', 'remtop'], subconfig_on_removetop_command),
            CommandHandler(['setchannel'], subconfig_on_setchannel_command),
            CommandHandler(['clonefrom'], subconfig_on_clonefrom_command),
            CommandHandler(['getstyle'], subconfig_on_getstyle_command),
            CommandHandler(['submissions'], subconfig_on_submissions_command),
            CommandHandler(['dailyavg'], subconfig_on_avgdaily_command),
            CommandHandler(['flairs'], subconfig_on_flairs_command),
            CommandHandler(['style'], subconfig_on_setstyle_command),
            CommandHandler(['sub', 'subreddit'], on_sub_command),
            CommandHandler(['cancel'], on_fake_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_waiting_subreddit_config_action_unknown_message),
        ],
        Status.SETCHANNEL_WAITING_CHANNEL: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), subconfig_on_selected_channel),
            MessageHandler(~Filters.command & Filters.all, subconfig_on_selected_channel_wrong),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_setchannel_waiting_channel_unknown_message),
        ],
        Status.SUBREDDIT_WAITING_STYLE: [
            MessageHandler(Filters.text & ~Filters.command, subconfig_on_style_selected),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_subreddit_waiting_style_unknown_message),
        ],
        Status.CLONE_WAITING_ORIGIN_SUBREDDIT: [
            MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), subconfig_on_origin_subreddit_selected),
            MessageHandler(~Filters.command & Filters.all, subconfig_on_selected_subreddit_wrong),
            CommandHandler(Command.CANCEL, on_cancel_command),
            MessageHandler(CustomFilters.all_but_regex(Command.EXIT_RE), on_clone_waiting_origin_subreddit_unknown_message),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)]
    },
    fallbacks=[CommandHandler(Command.EXIT, on_exit_command)],
    conversation_timeout=15 * 60
))
