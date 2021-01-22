import logging
import re
import time
from functools import wraps

from telegram import Update, Bot
from telegram.ext import ConversationHandler, CallbackContext

from bot.conversation import get_status_description
from bot.jobs.common.jobresult import JobResult
from database.models import Subreddit
from database.models import Job
from database.models import SubredditJob
from database import db
from sqlite3 import OperationalError
from utilities import u
from config import config

logger = logging.getLogger(__name__)


class Log:
    conv = logging.getLogger('conversation')
    handler = logging.getLogger('handler')
    job = logging.getLogger('job')


READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if update.effective_user.id not in config.telegram.admins:
            if update.effective_chat.id > 0:
                # only answer in private
                update.message.reply_text("You can't use this command")
            return

        return func(update, context, *args, **kwargs)

    return wrapped


def failwithmessage(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        try:
            return func(update, context, *args, **kwargs)
        except Exception as e:
            exc_info = True
            if 'database is locked' in str(e).lower():
                exc_info = False  # do not log the whole traceback if the error is 'database is locked'

            Log.handler.error('error during handler execution: %s', str(e), exc_info=exc_info)
            # logger.error('error during handler execution: %s', str(e), exc_info=exc_info)  # also log to main log file
            text = 'An error occurred while processing the message: <code>{}</code>'.format(u.escape(str(e)))

            if update.callback_query:
                update.callback_query.message.reply_html(text)
            else:
                update.message.reply_html(text)

    return wrapped


def logerrors(func):
    @wraps(func)
    def wrapped(context, *args, **kwargs):
        try:
            return func(context, *args, **kwargs)
        except Exception as e:
            Log.job.error('error during job execution: %s', str(e), exc_info=True)
            # logger.error('error during job execution: %s', str(e), exc_info=True)  # also log to main log file

    return wrapped


def knownsubreddit(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if context.args:
            sub_name = context.args[0]
            if not u.is_valid_sub_name(sub_name):
                update.message.reply_text('r/{} is not a valid subreddit name'.format(sub_name.lower()))
                return
            elif not Subreddit.fetch(sub_name):
                update.message.reply_text('No r/{} in the database'.format(sub_name.lower()))
                return

        return func(update, context, *args, **kwargs)

    return wrapped


def log_start_end_dt(func):
    @wraps(func)
    def wrapped(context: CallbackContext, *args, **kwargs):
        job_start_dt = u.now(utc=False)
        Log.job.info('%s job started at %s', context.job.name, job_start_dt.strftime(READABLE_TIME_FORMAT))

        with db.atomic():
            job_row = Job(name=context.job.name, start=job_start_dt)
            job_row.save()

        job_result: JobResult = func(context, job_row, *args, **kwargs)  # (posted_messages, uploaded_bytes)
        job_row.posted_messages = job_result.posted_messages
        job_row.uploaded_bytes = job_result.posted_bytes
        job_row.canceled = job_result.canceled

        job_end_dt = u.now(utc=False)
        job_row.end = job_end_dt

        elapsed_seconds = (job_end_dt - job_start_dt).total_seconds()
        job_row.duration = int(elapsed_seconds)

        with db.atomic():
            job_row.save()

        Log.job.info(
            '%s job ended at %s (elapsed seconds: %d (%s), posted messages: %d, uploaded data: %s)',
            context.job.name,
            job_start_dt.strftime(READABLE_TIME_FORMAT),
            elapsed_seconds,
            u.pretty_seconds(elapsed_seconds),
            job_row.posted_messages,
            u.human_readable_size(job_row.uploaded_bytes)
        )

        if elapsed_seconds > (config.jobs[context.job.name].interval * 60):
            text = '#maxfreq <{}> took more than its interval (frequency: {} min, elapsed: {} sec ({}), posted {} messages and uploaded {})'.format(
                context.job.name,
                config.jobs[context.job.name].interval,
                round(elapsed_seconds, 2),
                u.pretty_seconds(elapsed_seconds),
                job_row.posted_messages,
                u.human_readable_size(job_row.uploaded_bytes)
            )
            Log.job.warning(text)
            context.bot.send_message(config.telegram.log, text)

        return job_result

    return wrapped


def time_subreddit_processing(job_name=None):
    def real_decorator(func):
        @wraps(func)
        def wrapped(task, subreddit: Subreddit, bot: Bot, *args, **kwargs):
            processing_start_dt = u.now(utc=False)

            with db.atomic():
                job_row = SubredditJob(subreddit=subreddit, subreddit_name=subreddit.name, job_name=job_name, start=processing_start_dt)
                job_row.save()

            result: JobResult = func(task, subreddit, bot, *args, **kwargs)

            processing_end_dt = u.now(utc=False)
            job_row.end = processing_end_dt

            job_row.posted_messages = result.posted_messages
            job_row.uploaded_bytes = result.posted_bytes

            elapsed_seconds = (processing_end_dt - processing_start_dt).total_seconds()
            job_row.duration = elapsed_seconds

            with db.atomic():
                job_row.save()

            Log.job.info(
                'processing time for %s : %d seconds (%s)',
                subreddit.r_name_with_id,
                elapsed_seconds,
                u.pretty_seconds(round(elapsed_seconds, 2))
            )

            return result

        return wrapped

    return real_decorator


def deferred_handle_lock(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        while True:
            try:
                logger.debug('acquiring DEFERRED lock...')
                with db.atomic('DEFERRED'):
                    # http://docs.peewee-orm.com/en/latest/peewee/database.html#set-locking-mode-for-transaction

                    # acquire a peewee deferred lock: a sahred lock is acquired, but as soon as we need to write, it acquires a
                    # reserved lock. There can only be a reserved lock at time on a database, this means that if a
                    # function (handler) tries to write while the database is locked, an exception is raised. We
                    # try to run the handler until the lock is released.
                    # IMPORTANT: when a job runs, it acquires an 'EXCLUSIVE' lock which locks the database for
                    # everyone ('except for read uncommitted') so there shouldn't be any issue with jobs being blocked by a lock
                    # acquired by an handler because the job will acquire a lock when it start
                    # and will release it only when it ends
                    return func(update, context, *args, **kwargs)
            except OperationalError as e:
                if str(e) == 'database is locked':
                    logger.info('database is locked, sleeping')
                    time.sleep(1)
                else:
                    raise e

    return wrapped


def pass_subreddit_old(answer=False):
    def real_decorator(func):
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            ud = context.user_data.get(update.effective_user.id, {})

            subreddit = None
            if context.user_data and context.user_data.get('data', None) and context.user_data['data'].get('subreddit', None):
                subreddit = context.user_data['data']['subreddit']

            if not subreddit and answer:
                logger.debug('no subreddit previously selected (callback: %s)', func.__name__)
                update.message.reply_text('Ooops, you need to select a subreddit first. Use the /subreddit command to pick one')
                return ConversationHandler.END  # just in case we are in a conversation

            return func(update, context, subreddit=subreddit, *args, **kwargs)

        return wrapped

    return real_decorator


def pass_subreddit(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        subreddit = context.user_data['data']['subreddit']
        return func(update, context, subreddit=subreddit, *args, **kwargs)

    return wrapped


def no_ongoing_conversation(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        # the idea doesn't work, see https://github.com/RememberTheAir/reddit-test/issues/180#issuecomment-765367068
        if "data" in context.user_data:
            # what to do? There should be a way to retrun the previous conversation status (Status)
            Log.conv.debug("entry point <%s> triggered, but we are already inside a conversation", func.__name__)
            update.message.reply_text("This message triggers an entry point, but you cannot start another conversation. Use /exit to exit this one")
            previous_step = context.user_data["_last_returned_step"]
            return previous_step

        return func(update, context, *args, **kwargs)

    return wrapped


def pass_style(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        style = context.user_data['data']['style']
        return func(update, context, style=style, *args, **kwargs)

    return wrapped


def pass_channel(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        channel = context.user_data['data']['channel']
        return func(update, context, channel=channel, *args, **kwargs)

    return wrapped


def logconversation(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        step_returned = func(update, context, *args, **kwargs) or -10

        context.user_data["_last_returned_step"] = step_returned

        Log.conv.debug(
            'user %d: function <%s> returned step %d (%s)',
            update.effective_user.id,
            func.__name__,
            step_returned,
            get_status_description(step_returned)
        )

        if step_returned == -1:
            # -1 --> ConversationHandler.END
            # clean up temporrary data when the conversation ends
            # should be a decorator parameter
            tmp_keys = ["_last_returned_step", "data"]
            Log.conv.debug("conversation end: cleaning up temporary data: %s", ", ".join(tmp_keys))
            for key in tmp_keys:
                context.user_data.pop(key, None)

        return step_returned

    return wrapped
