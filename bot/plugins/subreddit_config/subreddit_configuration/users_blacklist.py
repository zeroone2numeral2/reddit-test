import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_ubl_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/ubl command')

    if not context.args:
        # just return the blacklist

        blacklist = subreddit.get_users_blacklist()
        if not blacklist:
            text = "Blacklist empty"
        else:
            text = "\n".join([u.username_to_link_but_cool(username) for username in blacklist])

        update.message.reply_html(text, disable_web_page_preview=True)

        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    username_lower = context.args[0].lower()

    username_url_html = u.username_to_link_but_cool(username_lower)

    if username_lower in subreddit.get_users_blacklist():
        subreddit.blacklist_user(username_lower, remove=True)
        action = "removed from the blacklist"
    else:
        subreddit.blacklist_user(username_lower, add=True)
        action = "added to the blacklist"

    update.message.reply_html('{} {}'.format(username_url_html, action), disable_web_page_preview=True)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
