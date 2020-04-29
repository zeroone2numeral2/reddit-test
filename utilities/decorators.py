import logging
import re
import time
from functools import wraps

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot.conversation import get_status_description
from database.models import Subreddit
from database.models import Job
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
            text = 'An error occurred while processing the message: <code>{}</code>'.format(u.escape(str(e)))
            update.message.reply_html(text)

    return wrapped


def logerrors(func):
    @wraps(func)
    def wrapped(context, *args, **kwargs):
        try:
            return func(context, *args, **kwargs)
        except Exception as e:
            Log.job.error('error during job execution: %s', str(e), exc_info=True)

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
        job_start_dt = u.now()
        Log.job.info('%s job started at %s', context.job.name, job_start_dt.strftime(READABLE_TIME_FORMAT))

        with db.atomic():
            job_row = Job(name=context.job.name, start=job_start_dt)

        job_result = func(context, *args, **kwargs)
        job_row.posted_messages = int(job_result)

        job_end_dt = u.now()
        job_row.end = job_end_dt

        elapsed_seconds = (job_end_dt - job_start_dt).total_seconds()
        job_row.duration = elapsed_seconds

        with db.atomic():
            job_row.save()

        Log.job.info(
            '%s job ended at %s (elapsed seconds: %d (%s))',
            context.job.name,
            job_start_dt.strftime(READABLE_TIME_FORMAT),
            elapsed_seconds,
            u.pretty_seconds(elapsed_seconds)
        )

        if elapsed_seconds > (config.jobs[context.job.name].interval * 60):
            text = '#maxfreq <{}> took more than its interval (frequency: {} min, elapsed: {} sec ({}))'.format(
                context.job.name,
                config.jobs[context.job.name].interval,
                round(elapsed_seconds, 2),
                u.pretty_seconds(elapsed_seconds)
            )
            Log.job.warning(text)
            context.bot.send_message(config.telegram.log, text)

        return job_result

    return wrapped


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


def pass_subreddit(answer=False):
    def real_decorator(func):
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            ud = updater.dispatcher.user_data.get(update.effective_user.id, {})

            subreddit = None
            if ud and ud.get('data', None) and ud['data'].get('subreddit', None):
                subreddit = ud['data']['subreddit']

            if not subreddit and answer:
                logger.debug('no subreddit previously selected (callback: %s)', func.__name__)
                update.message.reply_text('Ooops, you need to select a subreddit first. Use the /subreddit command to pick one')
                return ConversationHandler.END  # just in case we are in a conversation

            return func(update, context, subreddit=subreddit, *args, **kwargs)

        return wrapped

    return real_decorator


def logconversation(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        step_returned = func(update, context, *args, **kwargs)
        Log.conv.debug(
            'user %d: function <%s> returned step %d (%s)',
            update.effective_user.id,
            func.__name__,
            step_returned,
            get_status_description(step_returned)
        )

        return step_returned

    return wrapped
