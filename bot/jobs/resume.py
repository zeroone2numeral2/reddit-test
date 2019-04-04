import logging
import time
import datetime
from pprint import pprint

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import PostResume
from database import db
from reddit import reddit
from reddit import Sorting
from reddit import SenderResume
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def process_submissions(subreddit, bot):
    logger.info('fetching submissions')

    i = 0
    for submission in reddit.iter_top(subreddit.name, limit=15, period=subreddit.frequency):
        logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if PostResume.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                        submission.id)

            sender = SenderResume(bot, subreddit, submission)
            if not sender.test_filters():
                # do not return the object if it doesn't pass the filters
                logger.info('submission DID NOT pass the filters. continuing to the next submission...')
                continue

            yield sender
            i += 1
            if i >= subreddit.number_of_posts:
                # stop when we have returned the subreddit's number of posts
                break


def process_subreddit(subreddit, bot):
    logger.info('processing subreddit %s (r/%s) (frequency: %s)', subreddit.subreddit_id, subreddit.name, subreddit.frequency)

    now = u.now()
    weekday = datetime.datetime.today().weekday()
    if subreddit.frequency == 'week' and not (weekday == subreddit.weekday and subreddit.hour == now.hour):
        logger.info(
            'ignoring because -> subreddit.weekday != weekday (%d != %d) and subreddit.hour != current hour (%d != %d)',
            subreddit.weekday,
            weekday,
            subreddit.hour,
            now.hour
        )
        return
    elif subreddit.frequency == 'day' and now.hour != subreddit.hour:
        logger.info('ignoring because -> subreddit.hour != current hour (%d != %d)', subreddit.hour, now.hour)
        return

    elapsed_seconds = 0
    if subreddit.resume_last_posted_submission_dt:
        elapsed_seconds = (now - subreddit.last_posted_submission_dt).seconds

    if subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'day' and elapsed_seconds < 60*60):
        logger.info('ignoring subreddit because frequency is "day" and latest has been less than an hour ago')
        return
    elif subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'week' and elapsed_seconds < 60*60*24):
        logger.info('ignoring subreddit because frequency is "week" and latest has been less than a day ago')
        return

    annoucement_posted = False
    for sender in process_submissions(subreddit, bot):
        logger.info('submission url: %s', sender.submission.url)
        logger.info('submission title: %s', sender.submission.title)

        if not annoucement_posted:
            sender.post_resume_announcement()
            annoucement_posted = True

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
                sender.register_post()
            else:
                logger.info('not creating PostResume row: r/%s is a testing subreddit', subreddit.name)

            logger.info('updating Subreddit last *resume* post datetime...')
            subreddit.resume_last_posted_submission_dt = u.now()
            subreddit.save()

        time.sleep(1)


@Jobs.add(RUNNERS.run_repeating, interval=50*60, first=0, name='resume_job')
@d.logerrors
@d.log_start_end_dt
@db.atomic('IMMEDIATE')
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
