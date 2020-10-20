# noinspection PyPackageRequirements
from telegram.ext import MessageFilter

from bot import mainbot as updater


class SubredditSet(MessageFilter):
    def filter(self, message):
        if message.from_user:
            # print('ud get:', updater.dispatcher.user_data)
            ud = updater.dispatcher.user_data.get(message.from_user.id, {})
            if ud and ud.get('data', None) and ud['data'].get('subreddit', None):
                return True


class CustomFilters:
    subreddit_set = SubredditSet()
