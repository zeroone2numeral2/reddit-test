import logging
import time
from pprint import pprint

from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u
from utilities import d
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
            logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks', submission.id)
            
            return submission


def process_subreddit(subreddit, bot):
    logger.info('processing subreddit %s (r/%s)', subreddit.subreddit_id, subreddit.name)
    # logger.info('(subreddit: %s)', str(subreddit.to_dict()))

    if subreddit.last_posted_submission_dt:
        logger.info('elapsed time (now -- last post): %s -- %s', u.now(string=True),
                    subreddit.last_posted_submission_dt.strftime('%d/%m/%Y %H:%M'))
        elapsed_time_minutes = (u.now() - subreddit.last_posted_submission_dt).seconds / 60
    else:
        logger.info('(elapsed time cannot be calculated: no last submission datetime for the subreddit)')
        elapsed_time_minutes = 9999999

    if subreddit.last_posted_submission_dt and elapsed_time_minutes < subreddit.max_frequency:
        logger.info(
            'elapsed time is lower than max_frequency (%d minutes), continuing to next subreddit...',
            subreddit.max_frequency
        )
        return

    submission = process_submissions(subreddit)
    if not submission:
        logger.info('no submission returned, continuing to next subreddit/channel...')
        return

    sender = Sender(bot, subreddit.channel, subreddit, submission)

    if not sender.test_filters():
        logger.info('submission did not pass filters, marking it as processed...')
        sender.register_post()
        logger.info('continuing to next subreddit...')
        return

    try:
        sent_message = sender.post()
    except (BadRequest, TelegramError) as e:
        logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
        return
    except Exception as e:
        logger.error('generic error while posting the message: %s', str(e), exc_info=True)
        return

    if sent_message:
        logger.info('creating Post row...')
        sender.register_post()

        logger.info('updating Subreddit last post datetime...')
        subreddit.last_posted_submission_dt = u.now()
        subreddit.save()


@Jobs.add(RUNNERS.run_repeating, interval=10*60, first=0)
@d.logerrors
def check_posts(bot, job):
    logger.info('job started at %s', u.now(string=True))

    now = u.now(string=False)

    if config.quiet_hours.enabled and (now.hour > config.quiet_hours.start or now.hour < config.quiet_hours.end):
        logger.info('Quiet hours (%d - %d UTC): do not do anything (current hour UTC: %d)',
                    config.quiet_hours.start, config.quiet_hours.end, now.hour)
        return

    subreddits = (
        Subreddit.select()
    )

    for subreddit in subreddits:
        try:
            process_subreddit(subreddit, bot)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)

        time.sleep(1)

    logger.info('job ended at %s', u.now(string=True))
