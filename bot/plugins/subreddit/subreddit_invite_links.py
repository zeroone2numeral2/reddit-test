import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['links'])
@d.restricted
@d.failwithmessage
def links_command(_, update):
    logger.info('/links command')

    channels = Subreddit.get_invite_links()[:95]
    string_link = '• <a href="{invite_link}">r/{subreddits}</a> ({title} {channel_id})'
    string_no_link = '• r/{subreddits} ({title} {channel_id})'
    strings = list()
    for channel in channels:
        channel['subreddits'] = ', r/'.join(channel['subreddits'])
        if channel.get('invite_link', None):
            strings.append(string_link.format(**channel))
        else:
            strings.append(string_no_link.format(**channel))

    update.message.reply_html('\n'.join(strings), disable_web_page_preview=True)
