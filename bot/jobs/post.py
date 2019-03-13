import logging
import time
import datetime
from collections import namedtuple
from pprint import pprint

from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u
from database.models import Channel
from database.models import Subreddit
from database.models import Post
from reddit import reddit
from reddit import Sorting
from reddit import Sender
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)


def process_submissions(subreddit):
    logger.info('fetching submissions (sorting: %s)', subreddit.sorting)

    iterator = reddit.subreddit(subreddit.name).hot
    args = []
    kwargs = dict(limit=config.praw.submissions_limit)

    if subreddit.sorting == Sorting.TOP:
        iterator = reddit.subreddit(subreddit.name).top
        args = [Sorting.timeframe.DAY]
    elif subreddit.sorting == Sorting.NEW:
        iterator = reddit.subreddit(subreddit.name).new

    # logger.info('fetched submissions: %d', len(list(submissions)))

    for submission in iterator(*args, **kwargs):
        logger.info('checking submission: %s...', submission.id)
        if Post.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one', submission.id)
            return submission


# @Jobs.add(RUNNERS.run_daily, time=datetime.time(hour=4, minute=0))
@Jobs.add(RUNNERS.run_repeating, interval=5*60, first=0)
def check_posts(bot, job):
    logger.info('job started at %s', u.now(string=True))

    now = u.now(string=False)

    if config.quiet_hours.enabled and (now.hour > config.quiet_hours.start or now.hour < config.quiet_hours.end):
        logger.info('Quite hours (%d - %d): do not do anything (current hour: %d)',
                    config.quite_hours.start, config.quite_hours.end, now.hour)
        return

    channels = (
        Channel.select()
        #.where(Channel.enabled == True)
    )
    for channel in channels:
        logger.info('processing channel %d (%s)', channel.channel_id, channel.title)
        # logger.info('(channel: %s)', str(channel.to_dict()))

        subreddits = (
            Subreddit.select()
            .where(Subreddit.channel == channel)
        )

        for subreddit in subreddits:
            logger.info('channel %d: processing subreddit %s (r/%s)', channel.channel_id, subreddit.subreddit_id,
                        subreddit.name)
            # logger.info('(subreddit: %s)', str(subreddit.to_dict()))

            if subreddit.last_posted_submission_dt:
                logger.info('elapsed time (now -- last post): %s -- %s', u.now(string=True),
                            subreddit.last_posted_submission_dt.strftime('%d/%m/%Y %H:%M'))
                elapsed_time_minutes = (u.now(string=False) - subreddit.last_posted_submission_dt).seconds / 60
            else:
                logger.info('(elapsed time cannot be calculated: no last submission datetime for the subreddit)')


            if subreddit.last_posted_submission_dt and elapsed_time_minutes < subreddit.max_frequency:
                logger.info(
                    'elapsed time is lower than max_frequency (%d minutes), continuing to next subreddit...',
                    subreddit.max_frequency
                )
                continue

            submission = process_submissions(subreddit)
            if not submission:
                logger.info('no submission returned, continuing to next subreddit/channel...')
                continue

            sender = Sender(bot, channel, subreddit, submission)

            try:
                sent_message = sender.post()
            except (BadRequest, TelegramError) as e:
                logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
                continue
            except Exception as e:
                logger.error('generic error while posting the message: %s', str(e), exc_info=True)
                continue

            if sent_message:
                logger.info('creating Post row..')
                Post.create(
                    submission_id=sender.submission.id,
                    subreddit=subreddit,
                    channel=channel,
                    message_id=sent_message.message_id,
                    posted_at=u.now(string=False)
                )

                logger.info('updating Subreddit last post datetime...')
                subreddit.last_posted_submission_dt = u.now()
                subreddit.save()
