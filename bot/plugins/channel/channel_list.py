import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger(__name__)

STANDARD_TEST = """Full list of channels here (pinned message)

<b>Request a subreddit mirror</b>: https://telegra.ph/how-to-03-20"""


@Plugins.add(CommandHandler, command=['updatelist'])
@d.restricted
@d.failwithmessage
def on_channels_list(bot, update):
    logger.info('/updatelist command')

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

    steps = 50  # should be 100 (max number of entities)
    last_message_link, last_sent_message = None, None
    for i in range(0, len(lines), steps):
        chunk = lines[i:i + steps]
        text = '\n'.join(chunk)
        update.message.reply_text('{}\n{}'.format(len(text), len(chunk)))
        last_sent_message = bot.send_message('@' + config.telegram.index, text, disable_web_page_preview=True)

        last_message_link = u.message_link(last_sent_message)

    last_sent_message.reply_html(STANDARD_TEST)
