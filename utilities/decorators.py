import logging
from functools import wraps

from database.models import Subreddit
from database.models import Job
from utilities import u
from config import config

logger = logging.getLogger(__name__)

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if update.effective_user.id not in config.telegram.admins:
            if update.effective_chat.id > 0:
                # only answer in private
                update.message.reply_text("You can't use this command")
            return

        return func(bot, update, *args, **kwargs)

    return wrapped


def failwithmessage(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        try:
            return func(bot, update, *args, **kwargs)
        except Exception as e:
            logger.error('error during handler execution: %s', str(e), exc_info=True)
            text = 'An error occurred while processing the message: <code>{}</code>'.format(u.escape(str(e)))
            update.message.reply_html(text)

    return wrapped


def logerrors(func):
    @wraps(func)
    def wrapped(bot, job, *args, **kwargs):
        try:
            return func(bot, job, *args, **kwargs)
        except Exception as e:
            logger.error('error during job execution: %s', str(e), exc_info=True)

    return wrapped


def knownsubreddit(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if 'args' in kwargs:
            sub_name = kwargs['args'][0]
            if not u.is_valid_sub_name(sub_name):
                update.message.reply_text('r/{} is not a valid subreddit name'.format(sub_name.lower()))
                return
            elif not Subreddit.fetch(sub_name):
                update.message.reply_text('No r/{} in the database'.format(sub_name.lower()))
                return

        return func(bot, update, *args, **kwargs)

    return wrapped


def log_start_end_dt(func):
    @wraps(func)
    def wrapped(bot, job, *args, **kwargs):
        job_start_dt = u.now()
        logger.info('%s job started at %s', job.name, job_start_dt.strftime(READABLE_TIME_FORMAT))
        job_row = Job(name=job.name, start=job_start_dt)

        job_result = func(bot, job, *args, **kwargs)
        job_row.posted_messages = int(job_result)

        job_end_dt = u.now()
        job_row.end = job_end_dt

        elapsed_seconds = (job_end_dt - job_start_dt).total_seconds()
        job_row.duration = elapsed_seconds
        job_row.save()

        logger.info(
            '%s job ended at %s (elapsed seconds: %d (%s))',
            job.name,
            job_start_dt.strftime(READABLE_TIME_FORMAT),
            elapsed_seconds,
            u.pretty_seconds(elapsed_seconds)
        )

        if elapsed_seconds > (config.jobs[job.name].interval * 60):
            text = '#maxfreq <{}> took more than its interval (frequency: {} min, elapsed: {} sec ({}))'.format(
                job.name,
                config.jobs[job.name].interval,
                round(elapsed_seconds, 2),
                u.pretty_seconds(elapsed_seconds)
            )
            logger.warning(text)
            bot.send_message(config.telegram.log, text)

        return job_result

    return wrapped
