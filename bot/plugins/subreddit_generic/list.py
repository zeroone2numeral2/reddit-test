import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.models import Subreddit
from utilities import d
from utilities import u

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def subs_list(update: Update, context: CallbackContext):
    logger.info('/subs command')

    subreddits = Subreddit.get_list()
    if not subreddits:
        update.message.reply_text('The list is empty')
        return

    disabled_only = False
    if update.message.text.endswith("-d"):
        disabled_only = True
    
    strings = list()
    sub: Subreddit
    for i, sub in enumerate(subreddits):
        if disabled_only and sub.enabled:
            continue

        string = '{}. <code>{}</code> ({}, {})'.format(
            i + 1,
            sub.name,
            # sub.added.strftime('%d/%m/%Y') if sub.added else '??/??/????',
            sub.html_deeplink(context.bot.username, "⚙️"),
            sub.channel.title if sub.channel else 'no channel'
        )
        strings.append(string)

    for text in u.split_text(strings, join_by='\n'):
        update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['subs', 'list'], subs_list))
