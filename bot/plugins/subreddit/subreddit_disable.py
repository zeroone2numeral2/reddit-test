import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['disable'])
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_disable_command(_, update, subreddit):
    logger.info('/disable command')

    subreddit.enabled = False
    subreddit.enabled_resume = False
    subreddit.save()

    update.message.reply_html('/r/{s.name} (channel: {s.channel.title}) has been disabled'.format(s=subreddit))
