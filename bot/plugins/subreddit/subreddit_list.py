import logging

from telegram.ext import CommandHandler
from telegram import ParseMode

from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['subs', 'list'])
@d.restricted
@d.failwithmessage
def subs_list(bot, update):
    logger.info('/subs command')

    subreddits = Subreddit.get_list()
    if not subreddits:
        update.message.reply_text('The list is empty')
        return
    
    strings = list()
    for sub in subreddits:
        string = '<code>{}</code>'.format(sub.name)
        if sub.channel:
            string += ' ({})'.format(sub.channel.title)
        else:
            string += ' (no channel)'
        string += ' freq: {}'.format(u.pretty_minutes(sub.max_frequency))
        strings.append(string)

    update.message.reply_text('\n'.join(strings), parse_mode=ParseMode.HTML)
