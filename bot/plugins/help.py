import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import d

logger = logging.getLogger(__name__)

HELP_STRING = """\
/addchannel: register a channel (if already saved: updates its info)
/addsub `[subreddit name]`: register a subreddit
/setchannel `[subreddit name]`: change a subreddit's channel
/subs: list subreddits
/sub `[subreddit name]`: database row of that subreddit
/set `[subreddit name] [setting] [value]`: set "setting" to "value". "true", "True" will be converted to `True`, \
"false", "False" will be converted to `False`, "none", "None" will be converted to `None`
/get `[subreddit name] [setting]`: get the value of that setting
/remsub `[subreddit name]`: delete the subreddit from the database
/remchannel: remove a channel
/ph: list template's placeholders
/force `[job name]`: force that job
/d `[subreddit name] [hot|top|new]`: get the last 25 submission from teh subreddit, sorted by hot/top/new
/getconfig: see config values
/log: get the log file. Pass a number as argument if you want to get an archived log file
/db: get the database file
/utc: get current UTC time
/remdl: delete all the files in the downloads directory
/jobs: get the list of subreddits and their enabled jobs
/try `[submission id]`: get the submission with that id. Note: the subreddit must be saved in the database
/remffmpeglogs: remove ffmpeg log files
/loglines: get the date of the first line of every log file in the logs directory
/attr `[property]`: get the value of that property for all subreddits
/sdict `[subreddit]`: get the submission dict of the last post in that subreddit
"""


@Plugins.add(CommandHandler, command=['start', 'help'])
@d.restricted
@d.failwithmessage
def subs_list(_, update):
    logger.info('/help command')
    
    update.message.reply_markdown(HELP_STRING)
