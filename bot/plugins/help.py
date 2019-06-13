import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import d

logger = logging.getLogger(__name__)

HELP_STRING = """\
*Channels*
/addchannel: register a channel (if already saved: updates its info)
/remchannel: remove a channel
/updatetitles: update all the chat titles in the database
/setdesc: pin a pre-formatted message that describes the channel

*Subreddits*
/addsub `[subreddit name]`: register a subreddit
/setchannel `[subreddit name]`: change a subreddit's channel
/subs: list subreddits
/sub `[subreddit name]`: database row of that subreddit
/set `[subreddit name] [setting] [value]`: set "setting" to "value". "true", "True" will be converted to `True`, \
"false", "False" will be converted to `False`, "none", "None" will be converted to `None`
/get `[subreddit name] [setting]`: get the value of that setting
/remsub `[subreddit name]`: delete the subreddit from the database
/d `[subreddit name] [hot|top|new]`: get the last n submission from the subreddit, sorted by hot/top/new
/attr `[property]`: get the value of that property for all subreddits
/sdict `[subreddit]`: get the submission dict of the last post in that subreddit
/links: get a list of channels plus their links, if available
/icon `[subreddit]`: get that subreddit icon as a file (works with non saved subreddits)
/seticon `[subreddit]`: set the channel icon to that subreddit's icon
/exportlink: revoke and regenerate the invite link of a channel

*Logs*
/log `<log number>`: get the log file. Pass a number as argument if you want to get an archived log file
/loglines: get the date of the first line of every log file in the logs directory
/remffmpeglogs: remove ffmpeg log files

*Jobs*
/force `[job name]`: force that job
/jobs: get the list of subreddits and their enabled jobs
/duration `<job name>`: show the duration of the most recent 100 jobs executed. Can be filtered by job name

*Misc*
/ph: list template's placeholders
/getconfig: see config values
/remdl: delete all the files in the downloads directory
/db: get the database file
/now `<utc hour>`: get current UTC time and its localizations. If an hour is passed, times will be \
calculated at that UTC hour
/try `[submission id]`: get the submission with that id. Note: the subreddit must be saved in the database
forward a message posted by the bot in a channel: get that submission's dict
"""


@Plugins.add(CommandHandler, command=['start', 'help'])
@d.restricted
@d.failwithmessage
def subs_list(_, update):
    logger.info('/help command')
    
    update.message.reply_markdown(HELP_STRING)
