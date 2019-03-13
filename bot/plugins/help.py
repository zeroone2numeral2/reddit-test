import logging

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d

logger = logging.getLogger(__name__)

HELP_STRING = """\
/addchannel: register a channel
/addsub `[subreddit name]`: register a subreddit
/setchannel `[subreddit name]`: change a subreddit's channel
/subs: list subreddits
/sub `[subreddit name]`: database row of that subreddit
/set `[subreddit name] [setting] [value]`: set "setting" to "value". "true", "True" will be converted to `True`, \
"false", "False" will be converted to `False`, "none", "None" will be converted to `None`
/ph: list template's placeholders
"""


@Plugins.add(CommandHandler, command=['start', 'help'])
@d.restricted
@d.failwithmessage
def subs_list(bot, update):
    logger.info('/help command')
    
    update.message.reply_markdown(HELP_STRING)
