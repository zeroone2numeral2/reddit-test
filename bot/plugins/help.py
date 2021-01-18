import logging

from telegram.ext import CommandHandler

from bot import mainbot
from utilities import d

logger = logging.getLogger('handler')

HELP_STRING = """\
*Managing channels*
/addchannel `<username>`: save a channel (if already saved: updates its info)
/channel `<filter>`: manage a channel. The bot will list the available commands once a channel is selected
/updatechannels: update all the channels (title, username, invite link) in the database
/members: top 25 channels by number of members

*Managing subreddits/multireddits*
/addsub `[subreddit name] <channel title filter>`: register a subreddit
/addmulti `[creator] [multireddit name] <channel title filter>`: add a multireddit to a channel
/sub `<filter>`: change a subreddit configuration. The bot will list the available commands once a channel is selected
/subs: list all subreddits
/dailyposts: list all subreddits sorted by number of daily posts
/icon `[subreddit]`: get that subreddit icon as a file (works with non saved subreddits)
/optin `[subreddit]`: allow the current account to use the API to interact to a quarantined subreddit. Accepts any \
subreddit name

*Managing the channels catalogue*
/updatelist: update the catalogue channel's subreddits list

*Logs*
/remffmpeglogs: remove ffmpeg log files
/remlogs: remove log files

*Jobs*
/duration `<hours>`: show the average data of all jobs in the last week (or hours, if passed)
/lastjob: see when each job has ended the last time

*Styles*
/newstyle `[name]`: create a new style
/style `<filter>`: configure a style

*Misc*
/ph: list template's placeholders
/getconfig: see config values
/remdl: delete all the files in the downloads directory
/db: get the database file
/now `<utc hour>`: get current UTC time and its localizations. If an hour is passed, times will be \
calculated at that UTC hour
/try `[submission id]`: get the submission with that id (the subreddit doesn't need to be saved in the db)
/sdict `[submission id]`: get the submission dict of the submission (the subreddit doesn't need to be saved in the db)
forward a message posted by the bot in a channel: get that submission's dict
/credstats: get the usage of each account/client credentials
/credsusagemode: get (or change by passing a number) the usage mode of accounts and clients. Accepted values: 1, 2, 3, 0
/updateytdl: update the youtube-dl package using pip
/cleandb: delete old rows from some tables
"""


@d.restricted
@d.failwithmessage
def on_help_command(update, _):
    logger.info('/help command')
    
    update.message.reply_markdown(HELP_STRING)


mainbot.add_handler(CommandHandler(['start', 'help'], on_help_command))
