import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from reddit import reddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['optin', 'oi'], pass_args=True)
@d.restricted
@d.failwithmessage
def optin_quarantined(_, update, args):
    logger.info('/optin command')

    # Reference:
    # https://old.reddit.com/r/redditdev/comments/5vutzv/quaranopt_in_doesnt_seem_to_be_working/
    # https://old.reddit.com/r/redditdev/comments/asprwx/api_for_quarantined_subreddits/egw2n7l/

    if len(args) < 1:
        update.message.reply_text('Pass the subreddit name')
        return

    sub_name = args[0]
    try:
        subreddit = reddit.subreddit(sub_name)
        subreddit.quaran.opt_in()
        update.message.reply_text('Successfully opted-in, apparently')
    except Exception as e:
        update.message.reply_text('Exception while trying to opt-in to subreddit {}:'.format(sub_name))
        update.message.reply_html('<code>{}</code>'.format(u.html_escape(str(e))))