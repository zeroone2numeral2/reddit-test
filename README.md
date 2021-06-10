# Subreddits mirror bot

Stupidly simple bot horribly put together in a short time to provide a way to create Telegram channels that mirror one or more subreddits.

I made this bot so I could keep up with what's trending on some subreddits directly from Telegram. It is _not_ intended to be a data hoarding tool, althought one could tweak it to make it work like such a tool.

## Installation and configuration

1. clone this repository and `cd` it
2. Install the python requirements using `pip3 install -r requirements.txt`
3. rename `config.example.toml` to `config.toml`
4. rename `reddit.example.toml` to `reddit.toml`

### The `config.toml` file

This file _needs_ to be edited with various clients credentials before running the bot.
The values that you _must_ change are commented with `CHANGEME`. The other values don't need to be changed.

Some of the sections are not self explainatory or need further actions other than filling the required values, so I will try to give some context about them.

About the `[pyrogram]` section: [Pyrogram](https://docs.pyrogram.org/) is a Python MTProto client that is used to connect to the Telegram API and overcome some upload size limitations of the Rest API for bots.
To obtain your API id and hash, please refer to [Pyrogram's guide](https://docs.pyrogram.org/intro/setup#api-keys) about getting your credentials.

About the `[imgur]` section: it contains your Imgur client credentials that are used to interact with the Imgur API. You need them becase a lot of Reddit content is published through Imgur.

About the `[ffmpeg]` section: here you can define the command to invoke FFMPEG with on your system. FFMPEG is required to merge the video and audio streams of v.reddit videos.

Everything else in this file is either described trhough a comment, or you don't need to worry about it.

### The `reddit.toml` file

Thsi file contains your reddit accounts/clients credentials. It allows to use multiple accounts and clients to load-balance your requests.
The file structure is self-explanatory: each account can have one or more clients associeted, and you need to fill all the values of each account/client.

The first section of this file, `[general]`, allows deciding how to load-balance requests. Each mode is described by its comment.
Load-balancing is required to avoid to be rate-limited by the Reddit API. Requests to the Reddit API are sent by authenticating as an account + one of the clients it owns.
The preferred mode is `prefer_least_used_client`: to send requests, the bot will count the number of requests sent by each client during a period of time, and will use the one with the lower number of the requests sent in the past `stress_threshold_hours` hours.

### Starting the process

Once you've filled all the configuration files with the required information, run the bot with `python3 main.py`

## The process of fetching submissions to post on Telegram channels

To fecth the submissions to post on Telegram, a job runs every 10 minutes, pulling from Reddit the frontpage of every subreddit that needs to be checked.
10 minutes is a reasonable time interval that balances puntuality and workload.

The job frequency can be changed from `config.toml`, but I do not suggest to lower it too much, otherwise two consecutive jobs might overlap in case an operation takes more than expected to complete.

## Database migrations

There's a simple python file that executes database migrations on your config's sqlite file, using Peewee's built-in migrations tool.
The script is invoked every time the bot is started from `main.py`, but it can be ran manually:

```bash
python3 migrations.py
```

## So, how do I start tracking subreddits?

A few words about how the bot works. Initial configuration aside, everything can be configured from the bot: adding and configuring channels/subreddits is entirely handled from within your chat with the bot.

The main entities the bot works with are, of course, channels and subreddits/multireddits: you first configure your channels by adding them into the bot, and then add new sub/multireddits each one of them linked to a channel.

To configure a channel or a subreddit, you have to enter their configuration mode: once you've picked the channel/subreddit you want to configure, you will be able to use some specific commands to manage them.
Use `/exit` to exit a configuration conversation. You will automatically exit inactive conversations after 15 minutes.

### Main commands

Commands start by `/` only. `[this]` represents an optional command argument, `<this>` represents a required command argument.

Adding channels/subreddits/multireddits to the bot:

- `/addchannel [channel link/username]`: use this command to add a new channel to the managed channels list (the bot must be admin in that channel). Optionally accepts the channel's username/link, if it's public
- `/addsub <subreddit> [channel title filter]`: add a subreddit to a channel the bot is managing. You can append a word after the subreddit name that will be used to filter the channels list (the bot will ask you to pick a channel to add the subreddit to)
- `/addmulti <creator> <multireddit name> [channel title filter]`: add a multireddit. You must provide the username of its creator along with the multireddit name

Configuring a channel/subreddit/multireddit:

- `/channel [channel title filter]`: select a channel to configure from the added channels list. Once you've picked the channel, you will be able to configure it using some dedicated commands (see `/help` after picking a channel for more info)
- `/sub [sub/multireddit name filter]`: select a subreddit/multireddit to configure. Once you've picked it, you will be able to configure it using some dedicated commands (see `/help` after picking a subreddit for more info)

## Styles

Styles are special entities which basically handle the style of messages posted to Telegram, that is, how texts look like, what data to show, webpage previews, and so on.
Each subreddit is linked to a style, and you can create as much styles as you want.

- `/newstyle <style name>`: create a new style
- `/style`: configure an existing style (use `/help` after picking one to see the available commands)

### Other commands

There are many other commands: see `/help` (or read the code).

There's also a lot of things to say about configurations and other things. I don't think I have the time to sit down and describe how everything works. Maybe in the future.

## Supported content that will be uploaded to Telegram as media

The bot supports a number of medias:

- v.reddit videos (native Reddit videos)
- Reddit GIFs
- direct urls to mp4 videos
- direct urls to jpg/png images
- gfycat GIFs
- Imgur images/GIFs
- YouTube videos (needs to be enabled per-subreddit, the subreddit's `youtube_download` property must be set to `true`)

Every submission of this type that fails to send as media, will be sent as a text message.

## Disclaimer

This bot has been written in my spare time, it's horrible python, and is meant to be a personal tool for personal use, built on my needs: do not expect performances or code readability.

This project is open-source because some people requested me to tweak the instance I'm running to fit some of their needs - or asked for the bot to be used as a tool to pull all the media that was posted in one or more subreddits.
Unfortunately I don't have much time to work on customizations, requests or performances optimizations required by large loads of data to handle. So I decided to write this short readme so people can self-host an instance of the bot, and customize it to their needs as far as it's possible with this codebase.
