import logging
import os
import time
import datetime
from concurrent.futures import Future
from pprint import pprint

from telegram import ParseMode, Bot
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from .common.task import Task
from .common.threadpoolexecutor import MonitoredThreadPoolExecutor
from .common.jobresult import JobResult
from bot.logging import SubredditLogNoAdapter
from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import PostResume
from database import db
from reddit import reddit
from reddit import SenderResume
from utilities import u
from config import config

logger = logging.getLogger('job')

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def fetch_submissions(subreddit, bot):
    subreddit.logger.info('fetching submissions')

    i = 0
    if subreddit.sorting == 'hot':
        # we change the sorting way to 'day', because we can't get the 'top' submission from the period 'hot'
        subreddit.logger.warning('resume_job: changing "sorting" property of r/%s to "day"', subreddit.name)
        subreddit.sorting = 'day'
        with db.atomic():
            subreddit.save()

    for submission in reddit.iter_top(subreddit.name, limit=15, period=subreddit.sorting):
        subreddit.logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if PostResume.already_posted(subreddit, submission.id):
            subreddit.logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            subreddit.logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                                  submission.id)
            yield submission

            sender = SenderResume(bot, subreddit, submission)
            if not sender.test_filters():
                # do not return the object if it doesn't pass the filters
                subreddit.logger.info('submission DID NOT pass the filters. continuing to the next submission...')
                continue

            yield sender
            i += 1
            if i >= subreddit.number_of_posts:
                # stop when we have returned the subreddit's number of posts
                break


def is_time_to_process(subreddit: Subreddit) -> bool:
    subreddit.logger.info(
        'processing subreddit %s (r/%s) (frequency: %s, sorting: %s)',
        subreddit.subreddit_id,
        subreddit.name,
        subreddit.frequency,
        subreddit.sorting
    )

    now = u.now()
    weekday = datetime.datetime.today().weekday()
    if subreddit.frequency == 'week' and not (weekday == subreddit.weekday and subreddit.hour == now.hour):
        subreddit.logger.info(
            'ignoring because -> subreddit.weekday != weekday (%d != %d) and subreddit.hour != current hour (%d != %d)',
            subreddit.weekday,
            weekday,
            subreddit.hour,
            now.hour
        )
        return False
    elif subreddit.frequency == 'day' and now.hour != subreddit.hour:
        subreddit.logger.info('ignoring because -> subreddit.hour != current hour (%d != %d)', subreddit.hour, now.hour)
        return False

    elapsed_seconds = 999999
    if subreddit.resume_last_posted_submission_dt:
        subreddit.logger.info('resume_last_posted_submission_dt is not empty: %s',
                              subreddit.resume_last_posted_submission_dt.strftime('%d/%m/%Y %H:%M:%S'))
        elapsed_seconds = (now - subreddit.resume_last_posted_submission_dt).total_seconds()

    subreddit.logger.info('now: %s', now.strftime('%d/%m/%Y %H:%M:%S'))
    subreddit.logger.info('elapsed seconds from the last resume post: %d seconds (%s)', elapsed_seconds,
                          u.pretty_seconds(elapsed_seconds))

    if subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'day' and elapsed_seconds < 60 * 60):
        subreddit.logger.info('ignoring subreddit because frequency is "day" and latest has been less than an hour ago')
        return False
    elif subreddit.resume_last_posted_submission_dt and (subreddit.frequency == 'week' and elapsed_seconds < 60 * 60 * 24):
        subreddit.logger.info('ignoring subreddit because frequency is "week" and latest has been less than a day ago')
        return False


class SubredditTask(Task):
    # noinspection DuplicatedCode
    @d.time_subreddit_processing(job_name='resume')
    def __call__(self, subreddit: Subreddit, bot: Bot) -> JobResult:
        if self.interrupt_request:
            subreddit.logger.warning('received interrupt request: aborting subreddit processing')
            return JobResult()

        senders = list()
        for submission in fetch_submissions(subreddit, bot):
            if self.interrupt_request:
                subreddit.logger.warning('received interrupt request: aborting subreddit processing')
                return JobResult()

            subreddit.logger.info('submission url: %s', submission.url)
            subreddit.logger.info('submission title: %s', submission.title)

            sender = SenderResume(bot, subreddit, submission)
            if not sender.test_filters():
                # do not return the object if it doesn't pass the filters
                subreddit.logger.info('submission DID NOT pass the filters. continuing to the next submission...')
                continue

            senders.append(sender)
            if len(senders) >= subreddit.number_of_posts:
                # stop when we have returned the subreddit's number of posts
                break

        if not senders:
            subreddit.logger.info(
                'no (valid) submission returned for %s, continuing to next subreddit/channel...',
                subreddit.r_name_with_id)
            return JobResult()

        annoucement_posted = False
        job_result = JobResult()
        for sender in senders:
            if self.interrupt_request:
                subreddit.logger.warning('received interrupt request: aborting subreddit processing')
                return JobResult()

            if not annoucement_posted and subreddit.style.template_resume:
                sender.post_resume_announcement()
                annoucement_posted = True

            try:
                time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
                sent_message = sender.post()
            except (BadRequest, TelegramError) as e:
                subreddit.logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
                continue
            except Exception as e:
                subreddit.logger.error('generic error while posting the message: %s', str(e), exc_info=True)
                continue

            if sent_message:
                sender.register_post(test=subreddit.test)

                subreddit.logger.info('updating Subreddit last *resume* post datetime...')
                subreddit.resume_last_posted_submission_dt = u.now()
                with db.atomic():
                    subreddit.save()

                job_result.increment(posted_messages=1, posted_bytes=sender.uploaded_bytes)

            # time.sleep(1)

        return job_result


@d.logerrors
@d.log_start_end_dt
# @db.atomic('EXCLUSIVE')  # http://docs.peewee-orm.com/en/latest/peewee/database.html#set-locking-mode-for-transaction
def check_daily_resume(context: CallbackContext) -> JobResult:
    with db.atomic():  # noqa
        subreddits = (
            Subreddit.select()
            .where(Subreddit.enabled_resume == True, Subreddit.channel.is_null(False))
        )

    subreddits_to_process = list()
    for subreddit in subreddits:
        if not subreddit.style:
            subreddit.set_default_style()

        subreddit.logger = SubredditLogNoAdapter(subreddit)
        # subreddit.logger.set_subreddit(subreddit)

        if is_time_to_process(subreddit):
            subreddits_to_process.append(subreddit)

    if not subreddits_to_process:
        logger.info('no subreddit to process, exiting job')
        return JobResult()

    num_collected_subreddits = len(subreddits_to_process)
    logger.info('collected tasks: %d', num_collected_subreddits)

    max_workers = (os.cpu_count() or 1) * 2
    logger.info('max_workers: %d', max_workers)

    resume_job_result = JobResult()
    with MonitoredThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: [(SubredditTask, Future)] = list()
        for i, subreddit in enumerate(subreddits_to_process):
            logger.info('%d/%d submitting %s (id: %d)...', i+1, num_collected_subreddits, subreddit.r_name, subreddit.id)
            # future: Future = executor.submit(process_submissions, subreddit, context.bot)
            subreddit_task = SubredditTask()  # see https://stackoverflow.com/a/6514268
            future: Future = executor.submit(subreddit_task, subreddit, context.bot)
            future.subreddit = subreddit
            futures.append((subreddit_task, future))

        logger.info('harvesting results...')
        for subreddit_task, future in futures:
            # noinspection PyBroadException
            try:
                logger.info('waiting result for %s (id: %d)...', future.subreddit.name, future.subreddit.id)
                subreddit_job_result = future.result(timeout=context.job.interval)
                resume_job_result += subreddit_job_result
                logger.info('still %d active pools', executor.get_pool_usage())
            except TimeoutError:
                subreddit_task.request_interrupt()
                future.cancel()  # doesn't work apparently, the callback can't be stopped. We can only request its interruption
                logger.error('r/%s: processing took more than the job interval (cancelled: %s)', future.subreddit.name, future.cancelled())
                text = '#mirrorbot_error - pool executor timeout - %d seconds'.format(future.subreddit.name, context.job.interval)
                context.bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)
            except Exception:
                error_description = future.exception()
                future.subreddit.logger.error('error while processing subreddit r/%s: %s', future.subreddit.name, error_description, exc_info=True)
                text = '#mirrorbot_error - {} - <code>{}</code>'.format(future.subreddit.name, u.escape(error_description))
                context.bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        # time.sleep(1)

    return resume_job_result

