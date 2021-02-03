import logging
import logging.config
import time
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future
from concurrent.futures import TimeoutError

from telegram import ParseMode, Bot
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from .common.task import Task
from .common.threadpoolexecutor import MonitoredThreadPoolExecutor
from .common.jobresult import JobResult
from bot.logging import SubredditLogNoAdapter
from bot import botutils
from utilities import u
from utilities import d
from database.models import Subreddit, Job, Channel
from database.models import Post
from database.models import InitialTopPost
from database.models import RedditRequest
from database.queries import settings
from database.queries import reddit_request
from database import db
from reddit import Reddit
from reddit import creds
from reddit import Sender
from config import config, reddit as reddit_config

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
        return False


def calculate_quiet_hours_demultiplier(subreddit: Subreddit):
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

    if subreddit.last_post_datetime:
        subreddit.logger.info(
            'elapsed time (now -- last post): %s -- %s',
            now_string,
            subreddit.last_post_datetime.strftime('%d/%m/%Y %H:%M')
        )
        elapsed_time_minutes = (now - subreddit.last_post_datetime).total_seconds() / 60
    else:
        subreddit.logger.info('(elapsed time cannot be calculated: no last submission datetime for the subreddit)')
        elapsed_time_minutes = 9999999

    if subreddit.last_post_datetime and elapsed_time_minutes < calculated_max_frequency:
        subreddit.logger.info(
            'elapsed time is lower than max_frequency (%d*%d minutes), continuing to next subreddit...',
            subreddit.max_frequency,
            quiet_hours_demultiplier
        )
        return False
    else:
        return True


def get_default_reddit_instance():
    account = creds.default_account
    client = account.default_client

    reddit = Reddit(**account.creds_dict(), **client.creds_dict())

    return reddit, account.username, client.name


def get_reddit_instance(subreddit):
    usage_mode = settings.get_accounts_usage_mode()
    if usage_mode:
        subreddit.logger.debug('current usage mode: %s', usage_mode)

    if subreddit.reddit_client and creds.client_exists(subreddit.reddit_client):
        subreddit.logger.info('using subreddit client: %s', subreddit.reddit_client)

        client = creds.get_client_by_name(subreddit.reddit_client)
        account = creds.get_client_parent_account(subreddit.reddit_client)
    elif subreddit.reddit_account and creds.account_exists(subreddit.reddit_account):
        subreddit.logger.info('using subreddit account with least stressed client: %s', subreddit.reddit_account)
        account = creds.get_account_by_name(subreddit.reddit_account)

        client_name = reddit_request.least_stressed('client', account.client_names_list)[0]
        client = creds.get_client_by_name(client_name)
    elif usage_mode == 1 or (not usage_mode and reddit_config.general.prefer_default_account):
        # use the least used client of the default account
        subreddit.logger.info('using the default account and its least used client')

        account = creds.default_account
        client_name = reddit_request.least_stressed('client', account.client_names_list)[0]
        client = creds.get_client_by_name(client_name)
    elif usage_mode == 2 or (not usage_mode and reddit_config.general.prefer_least_used_account):
        subreddit.logger.info('using the least used account and its least used client')

        account_name = reddit_request.least_stressed('account', creds.account_names_list)[0]
        account = creds.get_account_by_name(account_name)
        client_name = reddit_request.least_stressed('client', account.client_names_list)[0]
        client = creds.get_client_by_name(client_name)
    elif usage_mode == 3 or (not usage_mode and reddit_config.general.prefer_least_used_client):
        subreddit.logger.info('using the least used client and its account')

        client_name = reddit_request.least_stressed('client', valid_names=creds.client_names_list)[0]
        client = creds.get_client_by_name(client_name)
        account = creds.get_client_parent_account(client_name)
    else:
        raise RuntimeError('uncatched scenario (usage_mode: {}, {})'.format(usage_mode, reddit_config.general))

    reddit = Reddit(**account.creds_dict(), **client.creds_dict())

    return reddit, account.username, client.name


def fetch_submissions(subreddit: Subreddit, reddit):
    subreddit.logger.info('fetching submissions (sorting: %s, is_multireddit: %s)', subreddit.sorting, str(subreddit.is_multireddit))

    limit = subreddit.limit or 25
    sorting = subreddit.sorting.lower()

    for position, submission in reddit.iter_submissions(subreddit.name, multireddit_owner=subreddit.multireddit_owner, sorting=sorting, limit=limit):
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

            # this is when we first send the request to fetch the comments: accessing a submission property
            # makes praw populate its attributes, and to do that it sends a request to the 'comments' endpoint
            if not hasattr(submission, 'current_position'):
                submission.current_position = position  # "position" starts from 1 and not 0

            yield submission


class SubredditTask(Task):
    # noinspection DuplicatedCode
    @d.time_subreddit_processing(job_name='stream')
    def __call__(self, subreddit: Subreddit, bot: Bot) -> JobResult:
        if self.interrupt_request:
            subreddit.logger.warning('received interrupt request: aborting subreddit processing')
            return JobResult()

        reddit, account_name, client_name = get_reddit_instance(subreddit)
        subreddit.logger.info('using account: %s, client: %s', account_name, client_name)

        # one reddit.iter_submissions() -> one request
        reddit_request.save_request(subreddit, account_name, client_name, description='submissions')

        senders = list()
        comments_requests_count = non_posted_submissions = 0  # we keep track of how many requests to fetch the comments we are going to send
        for submission in fetch_submissions(subreddit, reddit):
            comments_requests_count += 1  # we send it when we create the submission's 'current_position' attribute

            if self.interrupt_request:
                subreddit.logger.warning('received interrupt request: aborting subreddit processing')
                return JobResult()

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

        if non_posted_submissions < subreddit.number_of_posts:
            # we've been able to collect less submission than the number of required posts to post on each job.
            # This means that after fetching all the possible submission for the sub (based on Subreddit.limit) and
            # after filtering out already-posted submissions, we still weren't able to find enough submissions to
            # test and possibly send

            subreddit.logger.warning("unable to collect enough submissions to post: %d collected, %d required", non_posted_submissions, subreddit.number_of_posts)
            if subreddit.limit < Subreddit.limit.default:
                subreddit.logger.warning("subreddit's limit is lower than default, might want to adjust that")

                warning_hashtag = '#mirrorbot_warning_{}'.format(bot.username)
                text = '{} - {}: unable to fetch enough submissions to post (subreddit limit: {}, default limit: {})'.format(
                    warning_hashtag,
                    subreddit.r_name_with_id,
                    subreddit.limit,
                    Subreddit.limit.default
                )

                botutils.log(text=text, parse_mode=ParseMode.HTML)

        if not senders:
            subreddit.logger.info('no (valid) submission returned for r/%s, continuing to next subreddit/channel...',
                                  subreddit.name)
            return JobResult()

        # for each submission fetched, we have executed an additional request to fetch the comments
        reddit_request.save_request(subreddit, account_name, client_name, weight=comments_requests_count, description='comments')

        subreddit.logger.info('we collected %d/%d submissions to post', len(senders), subreddit.number_of_posts)

        job_result = JobResult()
        for sender in senders:
            if self.interrupt_request:
                subreddit.logger.warning('received cancel request: aborting subreddit processing')
                return job_result

            # we save this so we can understand how far in the frontpage we usually look through (max frontpage depth)
            # the method will increase it only if needed
            job_result.save_submission_max_index(sender.submission.current_position + 1)

            subreddit.logger.info('submission url: %s', sender.submission.url)
            subreddit.logger.info('submission title: %s', sender.submission.title)

            try:
                time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
                sent_messages = sender.post()
            except (BadRequest, TelegramError) as e:
                subreddit.logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
                continue
            except Exception as e:
                subreddit.logger.error('generic error while posting the message: %s', str(e), exc_info=True)
                continue

            if not sent_messages:
                subreddit.logger.warning(
                    'Sender.post() did not return any sent message, so we are NOT registering this submission and the last post datetime')
            else:
                if subreddit.test:
                    subreddit.logger.info(
                        'not creating Post row and not updating last submission datetime: r/%s is a testing subreddit',
                        subreddit.name
                    )
                else:
                    sender.register_post(test=subreddit.test)

                    subreddit.logger.info('updating Subreddit last post datetime...')
                    subreddit.last_post_datetime = u.now()

                    with db.atomic():
                        subreddit.save()

                job_result.increment(posted_messages=1, posted_bytes=sender.uploaded_bytes)

            # time.sleep(1)

        return job_result


def is_time_to_process(subreddit: Subreddit):
    quiet_hours_demultiplier = calculate_quiet_hours_demultiplier(subreddit)
    if quiet_hours_demultiplier == 0:  # 0: do not post anything if we are in the quiet hours timeframe
        subreddit.logger.info('quiet hours demultiplier of %s is 0: skipping posting during quiet hours', subreddit.r_name)
        return False

    if not time_to_post(subreddit, quiet_hours_demultiplier):
        return False

    return True


@d.logerrors
@d.log_start_end_dt
# @db.atomic('EXCLUSIVE')  # http://docs.peewee-orm.com/en/latest/peewee/database.html#set-locking-mode-for-transaction
def check_posts(context: CallbackContext, jobs_log_row: Job = None) -> JobResult:
    if settings.jobs_locked():
        logger.info('jobs are locked, skipping this job execution')
        return JobResult(canceled=True)

    bot = context.bot

    with db.atomic():
        subreddits = (
            Subreddit.select()
            .join(Channel)
            .where(Subreddit.enabled == True, Subreddit.channel.is_null(False), Channel.enabled == True)
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

    jobs_log_row.subreddits_count = num_collected_subreddits
    jobs_log_row.save()

    max_workers = (os.cpu_count() or 1) * 2
    logger.info('max_workers: %d', max_workers)

    executor_timeout = config.jobs.stream.interval * 60

    stream_job_result = JobResult()

    with MonitoredThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: [(SubredditTask, Future)] = list()
        for i, subreddit in enumerate(subreddits_to_process):
            logger.info('%d/%d submitting %s...', i+1, num_collected_subreddits, subreddit.r_name_with_id)
            # future: Future = executor.submit(process_submissions, subreddit, bot)
            subreddit_task = SubredditTask()  # see https://stackoverflow.com/a/6514268
            future: Future = executor.submit(subreddit_task, subreddit, bot)
            future.subreddit = subreddit
            futures.append((subreddit_task, future))

        logger.info('harvesting results...')
        for subreddit_task, future in futures:
            if settings.jobs_locked():
                logger.info('jobs have been locked, terminating subreddit tasks processing now and returning')
                stream_job_result.canceled = True
                return stream_job_result

            error_hashtag = '#mirrorbot_error_{}'.format(context.bot.username)

            # noinspection PyBroadException
            try:
                logger.info('waiting result for %s (id: %d)...', future.subreddit.name, future.subreddit.id)

                subreddit_job_result = future.result(timeout=executor_timeout)
                stream_job_result += subreddit_job_result

                logger.info('still %d active pools', executor.get_pool_usage())
            except TimeoutError:
                subreddit_task.request_interrupt()

                # future.cancel() doesn't work apparently, the callback can't be stopped. We can only request
                # its interruption. future.cancelled() will be False even after calling future.cancel()
                future.cancel()

                logger.error('r/%s: processing took more than the job interval (cancelled: %s)', future.subreddit.name, future.cancelled())

                text = '{} - pool executor timeout - {} seconds'.format(error_hashtag, executor_timeout)
                botutils.log(text=text, parse_mode=ParseMode.HTML)
            except Exception:
                error_description = str(future.exception())
                future.subreddit.logger.error('error while processing subreddit r/%s: %s', future.subreddit.name, error_description, exc_info=True)

                text = '{} - {} - <code>{}</code>'.format(
                    error_hashtag,
                    future.subreddit.r_name_with_id,
                    u.escape(error_description)
                )
                botutils.log(text=text, parse_mode=ParseMode.HTML)

            jobs_log_row.subreddits_progress += 1
            jobs_log_row.save()

        # time.sleep(1)

    return stream_job_result
