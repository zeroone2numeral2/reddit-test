import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from database.models import Subreddit
from database.queries import subreddits
from utilities import d
from utilities import u

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def subs_daily_posts_list(update: Update, _):
    logger.info('/dailyposts command')

    enabled_subreddits: [Subreddit] = subreddits.enabled_subreddits()
    if not subreddits:
        update.message.reply_text('No enabled subreddit')
        return

    enabled_subreddits.sort(key=lambda item: item.daily_posts, reverse=True)

    strings = list()
    for i, sub in enumerate(enabled_subreddits):
        string = '{}. {} ({})'.format(
            i + 1,
            sub.r_name_with_id,
            sub.daily_posts
        )
        strings.append(string)

    for text in u.split_text(strings, join_by='\n'):
        update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['dailyposts'], subs_daily_posts_list))
