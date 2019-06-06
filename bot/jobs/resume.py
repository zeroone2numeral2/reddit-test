import logging
import time
import datetime
from pprint import pprint

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Jobs
from ptbplugins.jobregistration import RUNNERS

from utilities import u
from utilities import d
from utilities import l
from database.models import Subreddit
from database.models import PostResume
from database import db
from reddit import reddit
from reddit import SenderResume
# from bot import Jobs
from config import config

logger = logging.getLogger('sp')

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def process_submissions(subreddit, bot):
    logger.info('fetching submissions')

    i = 0
    for submission in reddit.iter_top(subreddit.name, limit=15, period=subreddit.sorting):
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
    logger.info(
        'processing subreddit %s (r/%s) (frequency: %s, sorting: %s)',
        subreddit.subreddit_id,
        subreddit.name,
        subreddit.frequency,
        subreddit.sorting
    )

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
        return 0
    elif subreddit.frequency == 'day' and now.hour != subreddit.hour:
        logger.info('ignoring because -> subreddit.hour != current hour (%d != %d)', subreddit.hour, now.hour)
        return 0

    elapsed_seconds = 999999
    if subreddit.resume_last_posted_submission_dt:
        logger.info('resume_last_posted_submission_dt is not empty: %s', subreddit.resume_last_posted_submission_dt.strftime('%d/%m/%Y %H:%M:%S'))
        elapsed_seconds = (now - subreddit.resume_last_posted_submission_dt).total_seconds()

    logger.info('now: %s', now.strftime('%d/%m/%Y %H:%M:%S'))
    logger.info('elapsed seconds from the last resume post: %d seconds (%s)', elapsed_seconds, u.pretty_seconds(elapsed_seconds))

    if subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'day' and elapsed_seconds < 60*60):
        logger.info('ignoring subreddit because frequency is "day" and latest has been less than an hour ago')
        return 0
    elif subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'week' and elapsed_seconds < 60*60*24):
        logger.info('ignoring subreddit because frequency is "week" and latest has been less than a day ago')
        return 0

    annoucement_posted = False
    posted_messages = 0
    for sender in process_submissions(subreddit, bot):
        logger.info('submission url: %s', sender.submission.url)
        logger.info('submission title: %s', sender.submission.title)

        if not annoucement_posted and subreddit.template_resume:
            sender.post_resume_announcement()
            annoucement_posted = True

        try:
            time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
            sent_message = sender.post()
            posted_messages += 1
        except (BadRequest, TelegramError) as e:
            logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
            continue
        except Exception as e:
            logger.error('generic error while posting the message: %s', str(e), exc_info=True)
            continue

        if sent_message:
            if not subreddit.test:
                logger.info('creating PostResume row...')
                sender.register_post()
            else:
                logger.info('not creating PostResume row: r/%s is a testing subreddit', subreddit.name)

            logger.info('updating Subreddit last *resume* post datetime...')
            subreddit.resume_last_posted_submission_dt = u.now()
            subreddit.save()

        # time.sleep(1)

    return posted_messages


@Jobs.add(RUNNERS.run_repeating, interval=config.jobs.resume_job.interval * 60, first=config.jobs.resume_job.first * 60, name='resume_job')
@d.logerrors
@d.log_start_end_dt
@db.atomic('IMMEDIATE')
def check_daily_resume(bot, _):
    subreddits = (
        Subreddit.select()
        .where(Subreddit.enabled_resume == True)
    )

    total_posted_messages = 0
    for subreddit in subreddits:
        try:
            # l.set_logger_file('subredditprocessor', subreddit.name)
            posted_messages = process_subreddit(subreddit, bot)
            # l.set_logger_file('subredditprocessor')

            total_posted_messages += int(posted_messages)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)
            text = '#mirrorbot_error - {} - <code>{}</code>'.format(subreddit.name, u.escape(str(e)))
            bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        # time.sleep(1)

    return total_posted_messages
