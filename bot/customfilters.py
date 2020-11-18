import re

# noinspection PyPackageRequirements
from typing import Union, Pattern, cast

from telegram.ext import MessageFilter

from bot import mainbot as updater
from bot.plugins.commands import Command


class SubredditSet(MessageFilter):
    def filter(self, message):
        if message.from_user:
            # print('ud get:', updater.dispatcher.user_data)
            ud = updater.dispatcher.user_data.get(message.from_user.id, {})
            if ud and ud.get('data', None) and ud['data'].get('subreddit', None):
                return True


class AllButExit(MessageFilter):
    def filter(self, message):
        if message.text and re.search(Command.EXIT_RE, message.text, re.I):
            return False

        return True


class AllButRegex(MessageFilter):
    """filter everything but messages matching a regex"""

    def __init__(self, pattern: Union[str, Pattern]):
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.I)

        pattern = cast(Pattern, pattern)
        self.pattern: Pattern = pattern

    def filter(self, message):
        if message.text and self.pattern.search(message.text):
            return False

        return True


class CustomFilters:
    subreddit_set = SubredditSet()
    all_but_exit = AllButExit()
    all_but_regex = AllButRegex
