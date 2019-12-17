import logging

from telegram.ext import CommandHandler, CallbackContext
from telegram import ParseMode

from bot import mainbot
from database.models import Subreddit
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger(__name__)

STANDARD_TEXT = """Full list of channels here (pinned message)

<b>Request a subreddit mirror</b>: https://telegra.ph/how-to-03-20"""


@d.restricted
@d.failwithmessage
def on_channels_list(update, context: CallbackContext):
    logger.info('/updatelist command')

    # this whole function and the Subreddit method is a shitshow
    channels = Subreddit.get_channels()
    if not channels:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return

    lines = list()
    non_public_channels = list()
    i = 0
    for channel in channels:
        if channel.get('public', False):
            # do not post channels that are not public
            non_public_channels.append(channel['title'])
            continue

        i += 1

        channel_subreddits = list()
        for sub_id in channel['subreddits']:
            subreddit = Subreddit.get(id=int(sub_id))
            channel_subreddits.append(subreddit)

        # rebuild the list
        channel['subreddits'] = ['/{}/{}'.format('m' if s.is_multireddit else 'r', s.name) for s in channel_subreddits]

        line = '{i} • {added} • <a href="{invite_link}">link</a> • {subreddits}'.format(
            i=i,
            added=channel['added'].strftime('%d/%m/%Y'),
            subreddits=', '.join(channel['subreddits']),
            invite_link=channel['invite_link']
        )
        lines.append(line)

    first_message_link, first_sent_message = None, None
    for i, text in enumerate(u.split_text(lines, join_by='\n')):
        sent_message = context.bot.send_message('@' + config.telegram.index, text, disable_web_page_preview=True,
                                                parse_mode=ParseMode.HTML)

        if i == 0:
            first_sent_message = sent_message
            first_message_link = u.message_link(sent_message)

    final_message = first_sent_message.reply_html(STANDARD_TEXT)

    update.message.reply_text('Done {}'.format(u.message_link(final_message)), disable_web_page_preview=True)
    if non_public_channels:
        update.message.reply_text('Non-public channels ignored: {}'.format(', '.join(non_public_channels)))


mainbot.add_handler(CommandHandler('updatelist', on_channels_list))
