import logging

from telegram import Update

from bot.conversation import Status
from database.models import Subreddit
from database.models import InitialTopPost
from database.queries import reddit_request
from reddit import Reddit, creds
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_savetop_command(update: Update, _, subreddit: Subreddit):
    logger.info('/savetop command')

    account = creds.default_account
    client = account.default_client
    reddit = Reddit(**account.creds_dict(), **client.creds_dict())

    if subreddit.sorting not in ('month', 'all'):
        update.message.reply_text('This subreddit\'s sorting is not "month" or "all"')
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    reddit_request.save_request(subreddit, account.username, client.name, description='submissions')

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

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_removetop_command(update: Update, _, subreddit: Subreddit):
    logger.info('/removetop command')

    if subreddit.sorting not in ('month', 'all'):
        update.message.reply_text('This subreddit\'s sorting is not "month" or "all"')
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    query = InitialTopPost.delete().where(
        InitialTopPost.subreddit_name == subreddit.name,
        InitialTopPost.sorting == subreddit.sorting
    )
    removed = query.execute()

    update.message.reply_html('/r/{s.name}: removed {removed}/{s.limit} top posts ("{s.sorting}")'.format(
        s=subreddit,
        removed=removed
    ))
    update.message.reply_text('Warning! The initial top posts have been removed for all the channels relying on this subreddit with this sorting')

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_gettop_command(update: Update, _, subreddit: Subreddit):
    logger.info('/gettop command')

    if subreddit.sorting not in ('month', 'all'):
        update.message.reply_text('This subreddit\'s sorting is not "month" or "all"')
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    query = InitialTopPost.select().where(
        InitialTopPost.subreddit_name == subreddit.name,
        InitialTopPost.sorting == subreddit.sorting
    )
    top_posts = [p for p in query]

    update.message.reply_html('/r/{s.name}: currently saved {saved_n} top posts for current sorting "{s.sorting}", limit: {s.limit}'.format(
        s=subreddit,
        saved_n=len(top_posts)
    ))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
