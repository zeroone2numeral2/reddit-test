import datetime
import pytz
import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.models import Job
from database.queries import jobs
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def durations_command(update: Update, context: CallbackContext):
    logger.info('/duration command')

    hours = 24 * 7
    if context.args:
        hours = int(context.args[0])

    jobs_grouped = jobs.average(hours)
    if not jobs_grouped:
        update.message.reply_text('No job')

    text = 'Last {}:\n'.format(u.elapsed_smart_compact(hours * 60 * 60))
    for job in jobs_grouped:
        text += '\n- avg <code>{name}</code>: <b>{duration}</b>, {uploaded}, {subs} subs, {messages} msgs'.format(
            name=job.name,
            duration=u.pretty_seconds(job.avg_duration),
            uploaded=u.human_readable_size(job.avg_uploaded_bytes or 0),
            subs=job.avg_subreddits_count,
            messages=job.avg_posted_messages
        )

    update.message.reply_html(text)


@d.restricted
@d.failwithmessage
def lastjob_command(update: Update, _):
    logger.info('/lastjob command')

    text = ''
    for job_name, job_info in config.jobs.items():
        job_duration: Job = Job.last_job(job_name=job_name)

        if not job_duration:
            continue

        ended = "running"
        if job_duration.end:
            ended = job_duration.end_dt.strftime('%d/%m/%Y %H:%M:%S')

        now = u.now(utc=False)
        start_localized = u.replace_timezone(job_duration.start_dt, u.tz_DEFAULT)

        delta = now - start_localized
        diff_seconds = (10 * 60) + delta.total_seconds()  # I'm crying. It works only if I substract the timedelta from 10 minutes

        u.print_dt(now)
        u.print_dt(start_localized)
        print(diff_seconds)
        print(u.pretty_seconds(diff_seconds))

        # print(now.tzinfo, job_duration.end_dt.tzinfo, diff_seconds)

        started = "{} ({} ago)".format(
            job_duration.start_dt.strftime('%d/%m/%Y %H:%M:%S'),
            u.pretty_seconds(int(diff_seconds))
        )

        text += '\n\n<b>{name}</b>:\n• started: {started}\n• ended: {ended}\n• lasted: {elapsed}\n• every {interval} minutes\n• progress: {current}/{total} ({messages} messages, {bytes} uploaded)'.format(
            name=job_name,
            started=started,
            ended=ended,
            elapsed=u.pretty_seconds(job_duration.duration) if job_duration.duration is not None else 'running',
            interval=job_info['interval'],
            current=job_duration.subreddits_progress,
            total=job_duration.subreddits_count,
            messages=job_duration.posted_messages or '-',
            bytes=u.human_readable_size(job_duration.uploaded_bytes) or '-',
        )

    if not text:
        update.message.reply_text('No row in the database')
        return

    update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['duration', 'durations'], durations_command))
mainbot.add_handler(CommandHandler(['lastjob'], lastjob_command))
