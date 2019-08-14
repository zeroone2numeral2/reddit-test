import logging
from math import floor

from telegram.ext import CommandHandler
from telegram import MAX_MESSAGE_LENGTH
from telegram import ParseMode
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger(__name__)

STANDARD_TEXT = """Full list of channels here (pinned message)

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

    avg_line_length = int(sum(map(len, lines)) / len(lines))
    chunk_size = floor(MAX_MESSAGE_LENGTH/avg_line_length) - 10  # make sure to have a margin of some characters
    if chunk_size > 100:
        # should not exceed 100 (max number of entities)
        chunk_size = 100

    first_message_link, first_sent_message = None, None
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i:i + chunk_size]
        text = '\n'.join(chunk)
        sent_message = bot.send_message('@' + config.telegram.index, text, disable_web_page_preview=True,
                                        parse_mode=ParseMode.HTML)

        if i == 0:
            first_sent_message = sent_message
            first_message_link = u.message_link(sent_message)

    first_sent_message.reply_html(STANDARD_TEXT)
