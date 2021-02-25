import logging
import re

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Subreddit
from database.models import Style
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
def subconfig_on_setstyle_command(update: Update, context: CallbackContext):
    logger.info('/setstyle command, args: %s', str(context.args))

    # we consider the second argument as a filter for the destination subreddit selection keyboard
    name_filter = context.args[0].lower() if context.args else None

    styles: [Style] = Style.get_list(name_filter=name_filter)
    if not styles:
        update.message.reply_text('Cannot find any style (filter: {})'.format(name_filter))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    buttons_list = [style.name for style in styles]
    reply_markup = Keyboard.from_list(buttons_list)

    update.message.reply_text('Select the style (or /cancel):', reply_markup=reply_markup)

    return Status.SUBREDDIT_WAITING_STYLE


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_style_selected(update: Update, _, subreddit: Subreddit):
    logger.info('/style command: style selected (%s)', update.message.text)

    style = Style.by_name(update.message.text)
    if not style:
        update.message.reply_text('Select a style, or /cancel')
        return Status.SUBREDDIT_WAITING_STYLE

    subreddit.style = style
    subreddit.save()

    update.message.reply_html(
        'Style saved: <code>{}</code>'.format(style.name),
        disable_web_page_preview=True,
        reply_markup=Keyboard.REMOVE
    )

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_getstyle_command(update: Update, _, subreddit: Subreddit):
    logger.info('/getstyle command')

    text = u.model_dict(subreddit.style, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION

