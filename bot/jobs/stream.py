import logging
import logging.config
from logging.handlers import RotatingFileHandler
import time
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
from concurrent.futures import TimeoutError

from telegram import ParseMode, Bot
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from bot.logging import slogger
from bot.logging import SubredditLogNoAdapter
from const import JOB_NO_POST
from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import Post
from database.models import InitialTopPost
from database import db
from reddit import reddit
from reddit import Sender
from config import config

logger = logging.getLogger('job')

NOT_VALUES = (None, False)


def its_quiet_hours(subreddit: Subreddit):
    now = u.now()

    if subreddit.quiet_hours_start not in NOT_VALUES and subreddit.quiet_hours_end not in NOT_VALUES:
        subreddit.logger.info('subreddit has quiet hours (start/end: %d -> %d)', subreddit.quiet_hours_start,
                              subreddit.quiet_hours_end)
        if subreddit.quiet_hours_start >= subreddit.quiet_hours_end:
            if now.hour >= subreddit.quiet_hours_start or now.hour <= subreddit.quiet_hours_end:
                subreddit.logger.info('we are in the quiet hours timeframe (now: %d), ignoring...', now.hour)
                return True
        elif subreddit.quiet_hours_start < subreddit.quiet_hours_end:
            if subreddit.quiet_hours_start <= now.hour <= subreddit.quiet_hours_end:
                subreddit.logger.info('we are in the quiet hours timeframe (now: %d), ignoring...', now.hour)
                return True
        else:
            subreddit.logger.info('we are not in the quiet hours timeframe (hour: %d)', now.hour)
            return False
    else:
        # if the subreddit doesn't have the quiet hours configured, we use the config ones
        if now.hour >= config.quiet_hours.start or now.hour <= config.quiet_hours.end:
            subreddit.logger.info(
                'quiet hours (%d - %d UTC): do not do anything (current hour UTC: %d)',
                config.quiet_hours.start,
                config.quiet_hours.end, now.hour
            )
            return True
        else:
            return False


def calculate_quiet_hours_demultiplier(subreddit: Subreddit):
    if subreddit.quiet_hours_demultiplier is None:
        subreddit.quiet_hours_demultiplier = 0
        with db.atomic():
            subreddit.save()

    if subreddit.quiet_hours_demultiplier == 1:
        # if the multiplier is 1, no need to do other checks, the frequency is the same during quiet hours
        subreddit.logger.info('subreddit quiet hours demultiplier is 1: posts frequency is unchanged, no need to check if we are in quiet hours')
        return 1
    elif its_quiet_hours(subreddit):
        # if it's quiet hours: return the demultiplier
        return subreddit.quiet_hours_demultiplier
    else:
        subreddit.logger.info('we are not into the quiet hours timeframe: frequency multiplier is 1')
        return 1


def time_to_post(subreddit: Subreddit, quiet_hours_demultiplier):
    # we increase the max_frequency of the value set for the subreddit, so we can decrease the posting frequency
    # during quiet hours. If we are not in the quiet hours timeframe, the multplier will always be one,
    # so the max_frequency will be the same
    calculated_max_frequency = int(subreddit.max_frequency * quiet_hours_demultiplier)

    now = u.now()
    now_string = u.now(string=True)

    if subreddit.last_posted_submission_dt:
        subreddit.logger.info(
            'elapsed time (now -- last post): %s -- %s',
            now_string,
            subreddit.last_posted_submission_dt.strftime('%d/%m/%Y %H:%M')
        )
        elapsed_time_minutes = (now - subreddit.last_posted_submission_dt).total_seconds() / 60
    else:
        subreddit.logger.info('(elapsed time cannot be calculated: no last submission datetime for the subreddit)')
        elapsed_time_minutes = 9999999

    if subreddit.last_posted_submission_dt and elapsed_time_minutes < calculated_max_frequency:
        subreddit.logger.info(
            'elapsed time is lower than max_frequency (%d*%d minutes), continuing to next subreddit...',
            subreddit.max_frequency,
            quiet_hours_demultiplier
        )
        return False
    else:
        return True


def fetch_submissions(subreddit: Subreddit):
    subreddit.logger.info('fetching submissions (sorting: %s, is_multireddit: %s)', subreddit.sorting, str(subreddit.is_multireddit))

    limit = subreddit.limit or 25
    sorting = subreddit.sorting.lower()
    for submission in reddit.iter_submissions(subreddit.name, multireddit_owner=subreddit.multireddit_owner, sorting=sorting, limit=limit):
        subreddit.logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if Post.already_posted(subreddit, submission.id):
            subreddit.logger.info('...submission %s has already been posted', submission.id)
            continue
        elif subreddit.sorting.lower() in ('month', 'all') and InitialTopPost.is_initial_top_post(subreddit.name, submission.id, sorting):
            subreddit.logger.info('...subreddit has sorting "%s" and submission %s is among the initial top posts',
                         sorting, submission.id)
            continue
        else:
            subreddit.logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                                  submission.id)

            yield submission


class SubredditTask:
    def __init__(self):
        self.interrupt_request = False

    # noinspection DuplicatedCode
    @d.time_subreddit_processing(job_name='stream')
    def __call__(self, subreddit: Subreddit, bot: Bot):
        if self.interrupt_request:
            subreddit.logger.warning('received interrupt request: aborting subreddit processing')
            return JOB_NO_POST

        senders = list()
        for submission in fetch_submissions(subreddit):
            if self.interrupt_request:
                subreddit.logger.warning('received interrupt request: aborting subreddit processing')
                return JOB_NO_POST

            sender = Sender(bot, subreddit, submission)
            if sender.test_filters():
                subreddit.logger.info('submission %s ("%s") passed filters', submission.id, submission.title[:12])
                senders.append(sender)
                if len(senders) >= subreddit.number_of_posts:
                    subreddit.logger.info('we collected enough posts to post (number_of_posts: %d)',
                                          subreddit.number_of_posts)
                    break
            else:
                # no need to save ignored submissions in the database, because the next time
                # they might pass the filters
                # sender.register_ignored()
                subreddit.logger.info('submission di NOT pass filters, continuing to next one...')
                sender = None  # avoid to use a Sender that did not pass the filters
                continue

        if not senders:
            subreddit.logger.info('no (valid) submission returned for r/%s, continuing to next subreddit/channel...',
                                  subreddit.name)
            return JOB_NO_POST

        subreddit.logger.info('we collected %d/%d submissions to post', len(senders), subreddit.number_of_posts)

        posted_messages = 0
        posted_bytes = 0
        for sender in senders:
            if self.interrupt_request:
                subreddit.logger.warning('received cancel request: aborting subreddit processing')
                return JOB_NO_POST

            subreddit.logger.info('submission url: %s', sender.submission.url)
            subreddit.logger.info('submission title: %s', sender.submission.title)

            try:
                time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
                sent_message = sender.post()
            except (BadRequest, TelegramError) as e:
                subreddit.logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
                continue
            except Exception as e:
                subreddit.logger.error('generic error while posting the message: %s', str(e), exc_info=True)
                continue

            if not sent_message:
                subreddit.logger.warning(
                    'Sender.post() did not return any sent message, so we are NOT registering this submission and the last post datetime')
            else:
                if subreddit.test:
                    subreddit.logger.info(
                        'not creating Post row and not updating last submission datetime: r/%s is a testing subreddit',
                        subreddit.name)
                else:
                    subreddit.logger.info('creating Post row...')
                    sender.register_post()

                    subreddit.logger.info('updating Subreddit last post datetime...')
                    subreddit.last_posted_submission_dt = u.now()

                    with db.atomic():
                        subreddit.save()

                posted_messages += 1  # we posted one message
                posted_bytes += sender.uploaded_bytes

            # time.sleep(1)

        return posted_messages, posted_bytes

    def request_interrupt(self):
        self.interrupt_request = True


def is_time_to_process(subreddit: Subreddit):
    quiet_hours_demultiplier = calculate_quiet_hours_demultiplier(subreddit)
    if quiet_hours_demultiplier == 0:  # 0: do not post anything if we are in the quiet hours timeframe
        subreddit.logger.info('quiet hours demultiplier of r/%s is 0: skipping posting during quiet hours', subreddit.name)
        return False

    if not time_to_post(subreddit, quiet_hours_demultiplier):
        return False

    return True


class MonitoredThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_workers = 0

    def submit(self, *args, **kwargs):
        future = super().submit(*args, **kwargs)
        self._running_workers += 1
        future.add_done_callback(self._worker_is_done)
        return future

    def _worker_is_done(self, future):
        self._running_workers -= 1

    def get_pool_usage(self):
        return self._running_workers


@d.logerrors
@d.log_start_end_dt
# @db.atomic('EXCLUSIVE')  # http://docs.peewee-orm.com/en/latest/peewee/database.html#set-locking-mode-for-transaction
def check_posts(context: CallbackContext):
    with db.atomic():  # noqa
        subreddits = (
            Subreddit.select()
            .where(Subreddit.enabled == True, Subreddit.channel.is_null(False))
        )

    total_posted_messages = 0
    total_posted_bytes = 0
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
        return total_posted_messages, total_posted_bytes

    num_collected_subreddits = len(subreddits_to_process)
    logger.info('collected tasks: %d', num_collected_subreddits)

    max_workers = (os.cpu_count() or 1) * 2
    logger.info('max_workers: %d', max_workers)

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
                posted_messages, posted_bytes = future.result(timeout=context.job.interval)
                total_posted_messages += int(posted_messages)
                total_posted_bytes += posted_bytes
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

    return total_posted_messages, total_posted_bytes
