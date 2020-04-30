import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.models import Job
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def durations_command(update: Update, context: CallbackContext):
    logger.info('/duration command')

    if context.args:
        job_name = context.args[0]
    else:
        job_name = None

    durations = Job.durations(top=100, job_name=job_name)
    if not durations:
        update.message.reply_text('No row in the database')
        return

    strings_list = list()
    for duration in durations:
        strings_list.append('{0}: {2}/{3} ({start})'.format(*duration, start=duration[1].strftime('%d/%m/%Y %H:%M:%S')))

    update.message.reply_html('<code>$job_name: $seconds/$messages ($start)\n{}</code>'.format('\n'.join(strings_list)))


mainbot.add_handler(CommandHandler(['duration', 'durations'], durations_command, pass_args=True))
