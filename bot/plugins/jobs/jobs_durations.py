import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Job
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['duration', 'durations'], pass_args=True)
@d.restricted
@d.failwithmessage
def durations_command(_, update, args):
    logger.info('/duration command')

    if args:
        job_name = args[0]
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