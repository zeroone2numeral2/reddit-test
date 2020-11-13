import datetime
import logging
import time

from telegram import Update

from bot.conversation import Status
from database.models import Subreddit, Post
from database.queries import reddit_request
from reddit import Reddit, creds
from utilities import d
from utilities import u

logger = logging.getLogger('handler')

BASE_STRING = '<a href="{shortlink}">{i}</a>. [{posted}][<code>{id}</code>] {title} ({score}, {elapsed})'


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit
def subconfig_on_submissions_command(update: Update, _, subreddit: Subreddit):
    logger.info('/submissions command')

    update.message.reply_text('Fetching submissions...')

    limit = subreddit.limit or 25
    sorting = subreddit.sorting.lower()

    update.message.reply_text('Fetching submissions ({} from {})...'.format(limit, sorting))

    account = creds.default_account
    client = account.default_client
    reddit = Reddit(**account.creds_dict(), **client.creds_dict())

    lines = list()
    for i, submission in enumerate(reddit.iter_submissions(subreddit.name, multireddit_owner=subreddit.multireddit_owner,
                                                           sorting=sorting, limit=limit)):
        created_utc_dt = datetime.datetime.utcfromtimestamp(submission.created_utc)
        elapsed_seconds = (u.now() - created_utc_dt).total_seconds()
        elapsed_smart_compact = u.elapsed_smart_compact(elapsed_seconds)

        if Post.already_posted(subreddit, submission.id):
            posted = 'X'
        else:
            posted = ' '

        lines.append(BASE_STRING.format(
            i=i + 1,
            id=submission.id,
            title=submission.title,
            score=submission.score,
            elapsed=elapsed_smart_compact,
            posted=posted,
            shortlink=submission.shortlink
        ))

    reddit_request.save_request(subreddit, account.username, client.name)

    update.message.reply_html('\n'.join(lines))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
