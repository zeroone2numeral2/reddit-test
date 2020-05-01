import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_disable_command(update: Update, _, subreddit):
    logger.info('/disable command')

    subreddit.enabled = False
    subreddit.enabled_resume = False
    subreddit.save()

    update.message.reply_html('/r/{s.name} (channel: {s.channel.title}) has been disabled'.format(s=subreddit))


mainbot.add_handler(CommandHandler(['disable'], on_disable_command))
