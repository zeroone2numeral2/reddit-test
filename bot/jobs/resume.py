import logging
import time
from pprint import pprint

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import PostResume
from reddit import reddit
from reddit import Sorting
from reddit import Sender
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def process_submissions(subreddit, bot):
    logger.info('fetching submissions')

    i = 0
    for submission in reddit.iter_top(subreddit.name, subreddit.frequency, limit=15):
        logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if PostResume.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                        submission.id)

            sender = Sender(bot, subreddit, submission)
            if not sender.test_filters():
                # do not return the object if it doesn't pass the filters
                continue

            yield sender
            i += 1
            if i >= subreddit.number_of_posts:
                # stop when we have returned the subreddit's number of posts
                break


def process_subreddit(subreddit, bot):
    logger.info('processing subreddit %s (r/%s)', subreddit.subreddit_id, subreddit.name)

    for sender in process_submissions(subreddit, bot):
        logger.info('submission url: %s', sender.submission.url)
        logger.info('submission title: %s', sender.submission.title)

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
                logger.info('creating PostResume row...')
                sender.register_post_resume()
            else:
                logger.info('not creating PostResume row: r/%s is a testing subreddit', subreddit.name)


@Jobs.add(RUNNERS.run_repeating, interval=10*60, first=0, name='resume_job')
@d.logerrors
@d.log_start_end_dt
def check_daily_resume(bot, job):
    subreddits = (
        Subreddit.select()
        .where(Subreddit.enabled_resume == True)
    )

    for subreddit in subreddits:
        try:
            process_subreddit(subreddit, bot)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)
            text = '#mirrorbot_error - {} - <code>{}</code>'.format(subreddit.name, u.escape(str(e)))
            bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        time.sleep(1)
