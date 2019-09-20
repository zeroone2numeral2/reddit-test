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
    non_public_channels = list()
    for channel in channels:
        if not channel.get('public', None):
            # do not post channels that are not public
            non_public_channels.append(channel['title'])
            continue

        line = '• {added} • <a href="{invite_link}">link</a> • /r/{subreddits}'.format(
            added=channel['added'].strftime('%d/%m/%Y'),
            subreddits=', /r/'.join(channel['subreddits']),
            invite_link=channel['invite_link']
        )
        lines.append(line)

    first_message_link, first_sent_message = None, None
    for i, text in enumerate(u.split_text(lines, join_by='\n')):
        sent_message = bot.send_message('@' + config.telegram.index, text, disable_web_page_preview=True,
                                        parse_mode=ParseMode.HTML)

        if i == 0:
            first_sent_message = sent_message
            first_message_link = u.message_link(sent_message)

    final_message = first_sent_message.reply_html(STANDARD_TEXT)

    update.message.reply_text('Done {}'.format(u.message_link(final_message)), disable_web_page_preview=True)
    if non_public_channels:
        update.message.reply_text('Non-public channels ignored: {}'.format(', '.join(non_public_channels)))
