import logging

from telegram import Update

from bot.conversation import Status
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

IGNORE_KEYS = ('style',)


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_info_command(update: Update, _, subreddit: Subreddit):
    logger.info('/info command')

    text = u.model_dict(subreddit, plain_formatted_string=True, ignore_keys=IGNORE_KEYS)
    update.message.reply_html(text, disable_web_page_preview=True)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
