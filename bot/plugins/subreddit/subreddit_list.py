import logging

from telegram.ext import CommandHandler
from telegram import ParseMode
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['subs', 'list'])
@d.restricted
@d.failwithmessage
def subs_list(_, update):
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
        strings.append(string)

    update.message.reply_text('\n'.join(strings), parse_mode=ParseMode.HTML)
