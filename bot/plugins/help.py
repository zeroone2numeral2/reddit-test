import logging

from telegram.ext import CommandHandler

from bot import mainbot
from utilities import d

logger = logging.getLogger(__name__)

HELP_STRING = """\
*Adding and removing channels*
/addchannel: save a channel (if already saved: updates its info)
/remchannel: remove a channel

*Managing channels*
/updatetitles: update all the chat titles in the database
/setdesc: pin a pre-formatted message that describes the channel
/members: top 25 channels by number of members
/exportlink: revoke and regenerate the invite link of a channel

*Managing the channels catalogue*
/updatelist: update the catalogue channel's subreddits list

*Adding a subreddit/multireddit*
/addsub `[subreddit name]`: register a subreddit
/addmulti `[creator] [multireddit name]`: add a multireddit to a channel 

*Managing a subreddit's settings*
/sub `<filter>`: change a subreddit configuration. Optional filter to filter by subreddit's name the keyboard to \
select the subreddit from. When you use this command you'll enter the configuration mode of a subreddit, from \
there some commands can be used to edit its settings

*Other operations with subreddits*
/subs: list all subreddits
/d `[subreddit name] [hot|top|new]`: get the last n submission from the subreddit, sorted by hot/top/new
/sdict `[subreddit]`: get the submission dict of the last post in that subreddit
/links: get a list of channels plus their links, if available
/icon `[subreddit]`: get that subreddit icon as a file (works with non saved subreddits)
/optin `[subreddit]`: allow the current account to use the API to interact to a quarantined subreddit. Accepts any \
subreddit name

*Logs*
/log `<log number>`: get the log file. Pass a number as argument if you want to get an archived log file
/loglines: get the date of the first line of every log file in the logs directory
/remffmpeglogs: remove ffmpeg log files
/remsubslogs: remove the single subreddits' log files

*Jobs*
/force `[job name]`: force that job
/duration `<job name>`: show the duration of the most recent 100 jobs executed. Can be filtered by job name

*Misc*
/ph: list template's placeholders
/getconfig: see config values
/remdl: delete all the files in the downloads directory
/db: get the database file
/now `<utc hour>`: get current UTC time and its localizations. If an hour is passed, times will be \
calculated at that UTC hour
/try `[submission id]`: get the submission with that id (the subreddit doesn't need to be saved in the db)
forward a message posted by the bot in a channel: get that submission's dict
"""


@d.restricted
@d.failwithmessage
def on_help_command(update, _):
    logger.info('/help command')
    
    update.message.reply_markdown(HELP_STRING)


mainbot.add_handler(CommandHandler(['start', 'help'], on_help_command))
