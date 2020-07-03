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
