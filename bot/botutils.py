from config import config


def log(*args, raise_on_missing_logchat=False, **kwargs):
    from bot import mainbot

    if not config.telegram.get("log", None):
        if raise_on_missing_logchat:
            raise KeyError("config.telegram.bot not filled")
        else:
            return False

    kwargs.pop("chat_id", None)

    return mainbot.bot.send_message(config.telegram.log, *args, **kwargs)
