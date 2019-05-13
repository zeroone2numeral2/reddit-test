import logging

from telegram.ext import CommandHandler
from peewee import DoesNotExist
from ptbplugins import Plugins

from database.models import Post
from database.models import PostResume
from database.models import Subreddit
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['d'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def subs_debug(_, update, args):
    logger.info('/d command')

    if len(args) < 2:
        update.message.reply_text('Usage: /d [subreddit] [sorting]')
        return

    subreddit_name = args[0]
    sorting = args[1].lower()

    subreddit = Subreddit.fetch(subreddit_name)
    submissions = reddit.get_submissions(subreddit_name, sorting, limit=subreddit.limit)

    text = 'Sub id: <code>{}</code>\n'.format(submissions[0]['subreddit_id'])
    for submission in submissions:
        try:
            if subreddit.enabled:
                Post.get(Post.submission_id == submission['id'], Post.subreddit_id == submission['subreddit_id'])
                posted = 'posted'
            elif subreddit.enabled_resume:
                PostResume.get(PostResume.submission_id == submission['id'], PostResume.subreddit_id == submission['subreddit_id'])
                posted = 'posted'
        except DoesNotExist:
            posted = 'not posted'

        text += '\n• (((<code>{id}</code>/{elapsed_smart}/{score_dotted}/{posted}))) <b>{title_escaped}</b>'.format(**submission, posted=posted)

    update.message.reply_html(text)
