import logging

from telegram.ext import CommandHandler
from peewee import DoesNotExist

from bot import Plugins
from database.models import Post
from reddit import reddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBMISSION_FORMATTED = '• ((({elapsed_smart}/{score_dotted}))) <b>{title_escaped}</b>'


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

    text = 'Sub id: <code>{}</code>\n'.format(submissions[0]['subreddit_id'])
    for sub in submissions:
        try:
            Post.get(Post.submission_id == sub['id'], Post.submission_id == sub['subreddit_id'])
            posted = 'posted'
        except DoesNotExist:
            posted = 'not posted'

        text += '\n• (((<code>{id}</code>/{elapsed_smart}/{score_dotted}/{posted}))) <b>{title_escaped}</b>'.format(**sub, posted=posted)

    update.message.reply_html(text)
