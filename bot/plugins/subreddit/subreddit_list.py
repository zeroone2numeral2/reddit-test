import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from database.models import Subreddit
from utilities import d
from utilities import u

logger = logging.getLogger(__name__)


@d.restricted
@d.failwithmessage
def subs_list(update: Update, _):
    logger.info('/subs command')

    subreddits = Subreddit.get_list()
    if not subreddits:
        update.message.reply_text('The list is empty')
        return
    
    strings = list()
    for i, sub in enumerate(subreddits):
        string = '{}. <code>{}</code> ({}, {})'.format(
            i + 1,
            sub.name,
            sub.added.strftime('%d/%m/%Y') if sub.added else '??/??/????',
            sub.channel.title if sub.channel else 'no channel'
        )
        strings.append(string)

    for text in u.split_text(strings, join_by='\n'):
        update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['subs', 'list'], subs_list))
