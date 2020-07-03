import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from const import DEFAULT_TEMPLATES
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit_2
def subconfig_on_settemplate_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/settemplate command')

    if len(context.args) < 1:
        update.message.reply_text('Pass a template index (1-{}), or see them using /templates'.format(len(DEFAULT_TEMPLATES)))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    try:
        template = DEFAULT_TEMPLATES[int(context.args[0]) - 1]
    except (IndexError, ValueError):
        update.message.reply_text('Accepted values: 1-{}'.format(len(DEFAULT_TEMPLATES)))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    subreddit.template = template
    subreddit.save()

    update.message.reply_text('Template updated:')
    update.message.reply_html('<code>{}</code>'.format(template))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
