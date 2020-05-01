import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from database.models import InitialTopPost
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_savetop_command(update: Update, _, subreddit):
    logger.info('/savetop command')

    if subreddit.sorting not in ('month', 'all'):
        update.message.reply_text('This subreddit\'s sorting is not "month" or "all"')
        return

    duplicates = 0
    for submission in reddit.iter_top(name=subreddit.name, limit=subreddit.limit, period=subreddit.sorting):
        if InitialTopPost.is_initial_top_post(subreddit.name, submission.id, subreddit.sorting):
            duplicates += 1
            continue

        itp = InitialTopPost(submission_id=submission.id, subreddit_name=subreddit.name, sorting=subreddit.sorting)
        itp.save()

    update.message.reply_html('/r/{s.name}: saved {saved}/{s.limit} top posts ("{s.sorting}")'.format(
        s=subreddit,
        saved=subreddit.limit - duplicates
    ))


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_removetop_command(update: Update, _, subreddit):
    logger.info('/removetop command')

    query = InitialTopPost.delete().where(
        InitialTopPost.subreddit_name == subreddit.name,
        InitialTopPost.sorting == subreddit.sorting
    )
    removed = query.execute()

    update.message.reply_html('/r/{s.name}: removed {removed}/{s.limit} top posts ("{s.sorting}")'.format(
        s=subreddit,
        removed=removed
    ))
    update.message.reply('Warning! The initial top posts have been removed for all the channels relying on this subreddit with this sorting')


mainbot.add_handler(CommandHandler(['savetop'], on_savetop_command))
mainbot.add_handler(CommandHandler(['removetop'], on_removetop_command))
