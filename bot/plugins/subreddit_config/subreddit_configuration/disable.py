import logging

from telegram import Update

from bot.conversation import Status
from database.models import Subreddit
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_disable_command(update: Update, _, subreddit: Subreddit):
    logger.info('/disable command')

    subreddit.enabled = False
    subreddit.enabled_resume = False
    subreddit.save()

    update.message.reply_html('/r/{s.name} (channel: {title}) has been disabled'.format(s=subreddit, title=subreddit.channel_title()))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_enable_command(update: Update, _, subreddit: Subreddit):
    logger.info('/enable command')

    subreddit.enabled = True
    subreddit.save()

    update.message.reply_html('/r/{s.name} (channel: {title}) has been enabled'.format(s=subreddit, title=subreddit.channel_title()))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
