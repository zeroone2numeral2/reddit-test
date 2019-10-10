### Subreddits mirror bot

Stupidly simple bot horribly arranged in a short time to provide a way to create Telegram channels that mirror one or more subreddits, which are completely customizable from Telegram.

### Installation

1. `pip3 install -r requirements.txt`
2. rename `config.example.toml` to `config.toml` and change its values as you wish. "_CHANGEME_" values **need** to be changed with your API keys/tokens
3. `python3 main.py`


### Database migrations

There have been multiple database migrations during tests.
There's a simple python file that executes them on your config's sqlite file, using Peewee's built-in migrations tool

```bash
python3 migrations.py
```

### FFMPEG

An ffmpeg installation/binary is necessary to merge video and audio files of v.reddit videos.

On windows, it is necessary to have the binaries placed in the project root directory named `ffmpeg.exe`

On any other platform, it assumes you have ffmpeg installed and that it is possible to run ffmpeg from your shell.

### What are the commands?

Use `/help` or read the code.

### Disclaimer

This bot has been written in my spare time, it's horrible python, and is meant to be a personal tool for personal use, built on my needs.

Do not expect performances or readability.

### BotFather commands

```
help - get help
addchannel - save a channel
remchannel - remove a channel
updatetitles - update all the chat titles in the db
setdesc - pin the channel description
updatelist - update the channel's subreddits list
addsub - register a subreddit
addmulti - register a multireddit
setchannel - change a subreddit's channel
subs - list subreddits
sub - database row of that subreddit
set - change a subreddit setting
get - get the value of a setting
remsub - delete the subreddit from the database
d - get the last n submission from the subreddit, sorted by hot/top/new
attr - get the value of that property for all subreddits
sdict - get the submission dict of the last post in that subreddit
links - get a list of channels plus their links
icon - get that subreddit icon
seticon - set the channel icon
exportlink - regenerate the invite link of a channel
optin - interact with a quarantined subreddit
clone - clone the origin subreddit's settings
log - get the log file
loglines - get the date of the first line of every log file
remffmpeglogs - remove ffmpeg logs
force - force that job
jobs - get the list of subreddits and their enabled jobs
duration - show the duration of the most recent 100 jobs
members - top channels by number of members
ph - list template's placeholders
getconfig - see config values
remdl - empty the downloads directory
db - get the db file
now - get current UTC time
try - get the submission with that id
```