import logging
import re

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Subreddit
from database.models import Channel
from database.models import Style
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
def channelconfig_on_style_command(update: Update, context: CallbackContext):
    logger.info('/style command, args: %s', str(context.args))

    # we consider the second argument as a filter for the destination subreddit selection keyboard
    name_filter = context.args[0].lower() if context.args else None

    styles: [Style] = Style.get_list(name_filter=name_filter)
    if not styles:
        update.message.reply_text('Cannot find any style (filter: {})'.format(name_filter))
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    buttons_list = [style.name for style in styles]
    reply_markup = Keyboard.from_list(buttons_list)

    update.message.reply_text(
        'Select the style to apply to every subreddit in this channel (or /cancel):',
        reply_markup=reply_markup
    )

    return Status.CHANNEL_WAITING_STYLE


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_style_selected(update: Update, _, channel: Channel):
    logger.info('/style command: style selected (%s)', update.message.text)

    style = Style.by_name(update.message.text)
    if not style:
        update.message.reply_text('Select a style, or /cancel')
        return Status.CHANNEL_WAITING_STYLE

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    for subreddit in channel_subreddits:
        subreddit.style = style
        subreddit.save()
        logger.debug('updated style for subreddit %s', subreddit.r_name)

    update.message.reply_html(
        "Style saved for all this channel's subreddits: <code>{}</code>".format(style.name),
        disable_web_page_preview=True,
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def channelconfig_waiting_style_unknown_message(update: Update, context: CallbackContext):
    logger.info('CHANNEL_WAITING_STYLE: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a style or use /cancel"
    )

    return Status.CHANNEL_WAITING_STYLE
