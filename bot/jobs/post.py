import logging
import time
import datetime
from collections import namedtuple
from pprint import pprint

from utilities import u
from database.models import
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)


def process_submissions(channel, subreddit, submissions):
    for sub in submissions:
        if subreddit_submission_already_posted:
            continue
        else:
            return submission


@Jobs.add(RUNNERS.run_daily, time=datetime.time(hour=4, minute=0))
# @Jobs.add(RUNNERS.run_repeating, interval=5000, first=0)
def check_posts(bot, job):
    logger.info('job started at %s', u.now(string=True))

    if now.hour > config.quite_hours.start and now.hour < config.quite_jours.end:
        # don't post anything
        return

    # PSEUDOCODE
    for channel in channels:
        if not channel.enabled:
            continue

        for subreddit in channel.subreddits:
            if time_difference(now(), sub.reddit.last_posted_submission_dt) < subreddit.max_frequency:
                # do not post again if we posted less than the max frequency set
                continue

            submissions = get_submissions(subreddit.name, limit=50)

            submission_to_post = process_submissions(channel, subreddit, submissions)
            if not submission_to_post:
                continue

            sent_message = post_submission(submission, channel.images, channel.template)
            submission.save_latest_posted_submission_dt()
            channel.save_latest_post_datetime()
            post.create(sent_message, subreddit, submission)
