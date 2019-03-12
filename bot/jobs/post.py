import logging
import time
import datetime
from collections import namedtuple
from pprint import pprint

from utilities import u
from database.models import Channel
from database.models import Subreddit
from database.models import Post
from reddit import reddit
from reddit import SubmissionObject
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)


def process_submissions(channel, subreddit, submissions):
    for submission in submissions:
        logger.info('checking submission: %s...', submission.id)
        if Post.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one', submission.id)
            return SubmissionObject(submission, channel)


# @Jobs.add(RUNNERS.run_daily, time=datetime.time(hour=4, minute=0))
@Jobs.add(RUNNERS.run_repeating, interval=5000, first=0)
def check_posts(bot, job):
    logger.info('job started at %s', u.now(string=True))

    now = u.now(string=False)

    if config.quite_hours.enabled and (now.hour > config.quite_hours.start or now.hour < config.quite_jours.end):
        logger.info('Quite hours (%d - %d): do not do anything (current hour: %d)',
                    config.quite_hours.start, config.quite_hours.end, now.hour)
        return

    # PSEUDOCODE
    channels = (
        Channel.select()
        .where(Channel.enabled)
    )
    for channel in channels:
        logger.info('processing channel %d (%s)', channel.channel_id, channel.title)

        subreddits = (
            Subreddit.select()
            .where(Subreddit.channel == channel)
        )

        for subreddit in subreddits:
            logger.info('channel %d: processing subreddit %s (r/%s)', channel.channel_id, subreddit.subreddit_id,
                        subreddit.name)

            if subreddit.last_posted_submission_dt and \
                    ((u.now(string=False) - subreddit.last_posted_submission_dt).seconds / 60) < subreddit.max_frequency:
                logger.info(
                    'elapsed time (%s -- %s) is lower than max_frequency (%d minutes), continuing to next subreddit...',
                    u.now(string=True),
                    subreddit.last_posted_submission_dt.strftime('%d/%m/%Y %H:%M'),
                    subreddit.max_frequency
                )
                continue

            submissions = reddit.subreddit(subreddit.name).hot(limit=config.praw.submissions_limit)

            submission = process_submissions(channel, subreddit, submissions)
            if not submission:
                logger.info('no submission returned, continuing to next subreddit/channel...')
                continue

            sent_message = submission.post(bot)
            if sent_message:
                Post.create(
                    submission_id=submission.submission.id,
                    subreddit=subreddit,
                    channel=channel,
                    message_id=sent_message.message_id,
                    posted_at=u.now(string=False)
                )
