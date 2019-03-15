import logging

from telegram.ext import CommandHandler

from bot import Plugins
from reddit import reddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBMISSION_FORMATTED = '• ((({elapsed_smart}, {score_dotted}))) <b>{title_escaped}</b>'


@Plugins.add(CommandHandler, command=['d'], pass_args=True)
@d.restricted
@d.failwithmessage
def subs_debug(bot, update, args):
    logger.info('/d command')

    if len(args) < 2:
        update.message.reply_text('Usage: /d [subreddit] [sorting]')
        return

    subreddit = args[0]
    sorting = args[1].lower()

    submissions = reddit.get_submissions(subreddit, sorting)

    text = '\n'.join([SUBMISSION_FORMATTED.format(**sub) for sub in submissions])
    update.message.reply_html(text)
