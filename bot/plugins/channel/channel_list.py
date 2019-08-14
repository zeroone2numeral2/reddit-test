import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['channels'])
@d.restricted
@d.failwithmessage
def on_channels_list(_, update):
    logger.info('/channels command')

    channels = Subreddit.get_channels()
    if not channels:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return

    lines = list()
    for channel in channels:
        line = '• {added} • <a href="{invite_link}">link</a> • /r/{subreddits}'.format(
            added=channel['added'].strftime('%d/%m/%Y'),
            subreddits=', /r/'.join(channel['subreddits']),
            invite_link=channel['invite_link']
        )
        lines.append(line)

    for i in range(0, len(lines), 100):
        chunk = lines[i:i + 100]
        text = '\n'.join(chunk)
        update.message.reply_html(text, disable_web_page_preview=True)
