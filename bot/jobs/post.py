import logging
import time
from pprint import pprint

from telegram import ParseMode
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


def ignore_because_quiet_hours(subreddit):
    if subreddit.follow_quiet_hours is None:
        subreddit.follow_quiet_hours = True
        subreddit.save()

    if not subreddit.follow_quiet_hours:
        logger.info('r/%s does not follows quite hours: process submissions', subreddit.name)
        return False
    else:
        now = u.now(string=False)

        if now.hour > config.quiet_hours.start or now.hour < config.quiet_hours.end:
            logger.info('Quiet hours (%d - %d UTC): do not do anything (current hour UTC: %d)',
                        config.quiet_hours.start, config.quiet_hours.end, now.hour)
            return True
        else:
            return False


def process_submissions(subreddit):
    logger.info('fetching submissions (sorting: %s)', subreddit.sorting)

    limit = subreddit.limit or config.praw.submissions_limit
    for submission in reddit.iter_submissions(subreddit.name, subreddit.sorting.lower(), limit=limit):
        logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if Post.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks', submission.id)
            
            yield submission


def process_subreddit(subreddit, bot):
    logger.info('processing subreddit %s (r/%s)', subreddit.subreddit_id, subreddit.name)
    # logger.info('(subreddit: %s)', str(subreddit.to_dict()))

    if ignore_because_quiet_hours(subreddit):
        return

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
    
    submission, sender = None, None
    for submission in process_submissions(subreddit):
        sender = Sender(bot, subreddit, submission)
        if sender.test_filters():
            logger.info('submission passed filters')
            break
        else:
            sender.register_ignored()
            logger.info('submission di NOT pass filters, continuing to next one...')
            continue
        
    if not submission:
        logger.info('no submission returned for r/%s, continuing to next subreddit/channel...', subreddit.name)
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
        if not subreddit.test:
            logger.info('creating Post row...')
            sender.register_post()
        else:
            logger.info('not creating Post row: r/%s is a testing subreddit', subreddit.name)

        logger.info('updating Subreddit last post datetime...')
        subreddit.last_posted_submission_dt = u.now()
        subreddit.save()


@Jobs.add(RUNNERS.run_repeating, interval=10*60, first=0, name='posts_job')
@d.logerrors
def check_posts(bot, job):
    logger.info('job started at %s', u.now(string=True))

    subreddits = (
        Subreddit.select()
        .where(Subreddit.enabled == True)
    )

    for subreddit in subreddits:
        try:
            process_subreddit(subreddit, bot)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)
            text = '#mirrorbot_error - {} - <code>{}</code>'.format(subreddit.name, u.escape(str(e)))
            bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        time.sleep(1)

    logger.info('job ended at %s', u.now(string=True))
