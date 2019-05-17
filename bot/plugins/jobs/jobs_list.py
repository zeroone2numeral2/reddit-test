import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['jobs'])
@d.restricted
@d.failwithmessage
def jobs_command(_, update):
    logger.info('/jobs command')

    subs = Subreddit.subreddits_with_jobs()

    if not subs:
        update.message.reply_text('No subs')
        return

    subs_strings = list()
    for sub in subs:
        jobs = list()
        if sub[1]:
            jobs.append('post')
        if sub[2]:
            jobs.append('resume')

        subs_strings.append('r/{} ({})'.format(sub[0], ', '.join(jobs)))

    update.message.reply_text('\n'.join(subs_strings))
