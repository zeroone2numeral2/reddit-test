import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
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
    for i, sub in enumerate(subreddits):
        string = '{}. <code>{}</code> ({}, {})'.format(
            i + 1,
            sub.name,
            sub.added.strftime('%d/%m/%Y'),
            sub.channel.title if sub.channel else 'no channel'
        )
        strings.append(string)

    text = 'Subreddits ordered by addition date:\n\n{}'.format('\n'.join(strings))
    update.message.reply_html(text)
