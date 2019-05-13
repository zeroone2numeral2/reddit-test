import logging

from playhouse.shortcuts import model_to_dict
from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['attr'], pass_args=True)
@d.restricted
@d.failwithmessage
def sub_get_attributes(_, update, args):
    logger.info('/attr command (args: %s)', args)
    
    if len(args) < 1:
        update.message.reply_html('Use the following format: <code>/attr [property]</code>')
        return
    
    subreddits = (
        Subreddit.select()
        .where(Subreddit.enabled == True | Subreddit.enabled_resume == True)
        .order_by(+Subreddit.name)
    )
    if not subreddits:
        update.message.reply_text('No enabled subreddits')
        return
    
    prop = args[0]
    lines_list = list()
    for subreddit in subreddits:
        subreddit_dict = model_to_dict(subreddit)
        try:
            subreddit_dict[prop]
        except KeyError:
            update.message.reply_text('Could not find property "{}" (tested on r/{})'.format(prop, subreddit.name))
            return
        
        lines_list.append('{}: {}'.format(subreddit.name, str(subreddit_dict[prop])))
    
    text = '\n'.join(lines_list)
    update.message.reply_html(text)
