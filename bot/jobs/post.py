import logging
import time
import datetime
from collections import namedtuple
from pprint import pprint

from utilities import u
from database.models import Channel
from database.models import Subreddit
from reddit import reddit
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)


def process_submissions(channel, subreddit, submissions):
    for sub in submissions:
        submission = SubmissionObject(sub)
        if submission.duplicate():
            continue
        else:
            return submission


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
                continue

            sent_message = submission.send(channel)  # also saves last post datetime of the channel database object
            submission.save_latest_posted_submission_dt()
            post.create(sent_message, subreddit, submission)
