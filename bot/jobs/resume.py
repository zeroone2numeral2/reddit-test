import logging
import time
import datetime
from pprint import pprint

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from bot.logging import slogger
from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import PostResume
from database import db
from reddit import reddit
from reddit import SenderResume
from config import config

logger = logging.getLogger('job')

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def process_submissions(subreddit, bot):
    slogger.info('fetching submissions')

    i = 0
    if subreddit.sorting == 'hot':
        # we change the sorting way to 'day', because we can't get the 'top' submission from the period 'hot'
        slogger.warning('resume_job: changing "sorting" property of r/%s to "say"', subreddit.name)
        subreddit.sorting = 'day'
        with db.atomic():
            subreddit.save()

    for submission in reddit.iter_top(subreddit.name, limit=15, period=subreddit.sorting):
        slogger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if PostResume.already_posted(subreddit, submission.id):
            slogger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            slogger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                        submission.id)

            sender = SenderResume(bot, subreddit, submission)
            if not sender.test_filters():
                # do not return the object if it doesn't pass the filters
                slogger.info('submission DID NOT pass the filters. continuing to the next submission...')
                continue

            yield sender
            i += 1
            if i >= subreddit.number_of_posts:
                # stop when we have returned the subreddit's number of posts
                break


def process_subreddit(subreddit, bot):
    slogger.info(
        'processing subreddit %s (r/%s) (frequency: %s, sorting: %s)',
        subreddit.subreddit_id,
        subreddit.name,
        subreddit.frequency,
        subreddit.sorting
    )

    now = u.now()
    weekday = datetime.datetime.today().weekday()
    if subreddit.frequency == 'week' and not (weekday == subreddit.weekday and subreddit.hour == now.hour):
        slogger.info(
            'ignoring because -> subreddit.weekday != weekday (%d != %d) and subreddit.hour != current hour (%d != %d)',
            subreddit.weekday,
            weekday,
            subreddit.hour,
            now.hour
        )
        return 0
    elif subreddit.frequency == 'day' and now.hour != subreddit.hour:
        slogger.info('ignoring because -> subreddit.hour != current hour (%d != %d)', subreddit.hour, now.hour)
        return 0

    elapsed_seconds = 999999
    if subreddit.resume_last_posted_submission_dt:
        slogger.info('resume_last_posted_submission_dt is not empty: %s', subreddit.resume_last_posted_submission_dt.strftime('%d/%m/%Y %H:%M:%S'))
        elapsed_seconds = (now - subreddit.resume_last_posted_submission_dt).total_seconds()

    slogger.info('now: %s', now.strftime('%d/%m/%Y %H:%M:%S'))
    slogger.info('elapsed seconds from the last resume post: %d seconds (%s)', elapsed_seconds, u.pretty_seconds(elapsed_seconds))

    if subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'day' and elapsed_seconds < 60*60):
        slogger.info('ignoring subreddit because frequency is "day" and latest has been less than an hour ago')
        return 0
    elif subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'week' and elapsed_seconds < 60*60*24):
        slogger.info('ignoring subreddit because frequency is "week" and latest has been less than a day ago')
        return 0

    annoucement_posted = False
    posted_messages = 0
    for sender in process_submissions(subreddit, bot):
        slogger.info('submission url: %s', sender.submission.url)
        slogger.info('submission title: %s', sender.submission.title)

        if not annoucement_posted and subreddit.template_resume:
            sender.post_resume_announcement()
            annoucement_posted = True

        try:
            time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
            sent_message = sender.post()
            posted_messages += 1
        except (BadRequest, TelegramError) as e:
            slogger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
            continue
        except Exception as e:
            slogger.error('generic error while posting the message: %s', str(e), exc_info=True)
            continue

        if sent_message:
            if not subreddit.test:
                slogger.info('creating PostResume row...')
                sender.register_post()
            else:
                sinfo('not creating PostResume row: r/%s is a testing subreddit', subreddit.name)

            slogger.info('updating Subreddit last *resume* post datetime...')
            subreddit.resume_last_posted_submission_dt = u.now()
            with db.atomic():
                subreddit.save()

        # time.sleep(1)

    return posted_messages


@d.logerrors
@d.log_start_end_dt
# @db.atomic('IMMEDIATE')
def check_daily_resume(context: CallbackContext):
    with db.atomic():
        subreddits = (
            Subreddit.select()
            .where(Subreddit.enabled_resume == True, Subreddit.channel.is_null(False))
        )

    total_posted_messages = 0
    for subreddit in subreddits:
        slogger.set_subreddit(subreddit)
        try:
            posted_messages = process_subreddit(subreddit, context.bot)
            total_posted_messages += int(posted_messages)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)
            text = '#mirrorbot_error - {} - <code>{}</code>'.format(subreddit.name, u.escape(str(e)))
            context.bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        # time.sleep(1)

    return total_posted_messages
