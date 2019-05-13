import datetime
import os
import urllib.request

import praw
from prawcore.exceptions import Redirect

from .sortings import Sorting
from utilities import u
from config import config


class Reddit(praw.Reddit):
    def __init__(self, *args, **kwargs):
        praw.Reddit.__init__(self,  *args, **kwargs)
    
    def subreddit_exists(self, name):
        try:
            subreddit = self.subreddit(name)
            return str(subreddit.display_name)  # save the correct name
        except Redirect:
            return False

    def get_submissions(self, subreddit, sorting='hot', limit=config.praw.submissions_limit):
        result = list()
        for submission in self.iter_submissions(subreddit, sorting, limit):
            created_utc_dt = datetime.datetime.utcfromtimestamp(submission.created_utc)

            result.append(dict(
                subreddit_id=submission.subreddit_id,
                id=submission.id,
                title_escaped=u.escape(submission.title),
                score_dotted=u.dotted(submission.score or 0),
                elapsed_smart=u.elapsed_time_smart((u.now() - created_utc_dt).seconds)
            ))

        return result

    def iter_submissions(self, name, sorting='hot', limit=config.praw.submissions_limit):
        iterator = self.subreddit(name).hot
        args = []
        kwargs = dict(limit=limit)

        if sorting == Sorting.TOP:
            iterator = self.subreddit(name).top
            args = [Sorting.timeframe.DAY]
        elif sorting == Sorting.NEW:
            iterator = self.subreddit(name).new

        for submission in iterator(*args, **kwargs):
            yield submission

    def iter_top(self, name, limit, period='day'):
        for submission in self.subreddit(name).top(period, limit=limit):
            yield submission

    def get_icon(self, sub_name, download=False):
        try:
            sub = self.subreddit(sub_name)
        except Redirect:
            return

        try:
            icon_url = sub.icon_img
            if not icon_url:  # sometimes it's an empty string
                return
        except (AttributeError, Redirect):
            return

        if download:
            file_path = os.path.join('downloads', 'icon_{}.png'.format(sub_name))

            with urllib.request.urlopen(icon_url) as response, open(file_path, 'wb') as out_file:
                data = response.read()
                out_file.write(data)

            return file_path
        else:
            return icon_url
