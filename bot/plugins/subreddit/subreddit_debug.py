import logging

from telegram.ext import CommandHandler
from peewee import DoesNotExist
from ptbplugins import Plugins

from database.models import Post
from database.models import Ignored
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['d'], pass_args=True)
@d.restricted
@d.failwithmessage
def subs_debug(_, update, args):
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
            Post.get(Post.submission_id == sub['id'], Post.subreddit_id == sub['subreddit_id'])
            posted = 'posted'
        except DoesNotExist:
            posted = 'not posted'
            # if the submission has not been posted, check if it has been ignored
            if Ignored.ignored(sub['id'], sub['subreddit_id']):
                posted = 'ignored'
            

        text += '\n• (((<code>{id}</code>/{elapsed_smart}/{score_dotted}/{posted}))) <b>{title_escaped}</b>'.format(**sub, posted=posted)

    update.message.reply_html(text)
