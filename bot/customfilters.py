# noinspection PyPackageRequirements
from telegram.ext import BaseFilter

from bot import updater


class SubredditSet(BaseFilter):
    def filter(self, message):
        if message.from_user:
            print(message.text, updater.dispatcher.user_data)
            ud = updater.dispatcher.user_data.get(message.from_user.id, {})
            if ud and ud.get('data', None) and ud['data'].get('subreddit', None):
                return True


class CustomFilters:
    subreddit_set = SubredditSet()
