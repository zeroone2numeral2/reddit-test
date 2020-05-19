import datetime
import os
import urllib.request

import praw
from prawcore.exceptions import Redirect
from prawcore.exceptions import NotFound

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
        except (Redirect, NotFound):
            return False

    def multireddit_exists(self, redditor, name):
        try:
            multireddit = self.multireddit(redditor=redditor, name=name)
            if multireddit.visibility != 'public':
                # the API doesn't allow to request submissions from private multis
                return False

            return str(multireddit.name)  # save the correct name
        except (Redirect, NotFound):
            return False

    def get_submissions(self, subreddit, multireddit_owner=False, sorting='hot', limit=config.praw.submissions_limit):
        result = list()
        for submission in self.iter_submissions(subreddit, multireddit_owner=multireddit_owner, sorting=sorting, limit=limit):
            created_utc_dt = datetime.datetime.utcfromtimestamp(submission.created_utc)

            result.append(dict(
                subreddit_id=submission.subreddit_id,
                id=submission.id,
                title_escaped=u.escape(submission.title),
                score_dotted=u.dotted(submission.score or 0),
                elapsed_smart=u.elapsed_time_smart((u.now() - created_utc_dt).seconds)
            ))

        return result

    def iter_submissions(self, name, multireddit_owner=None, sorting='hot', limit=config.praw.submissions_limit):
        if not multireddit_owner:
            iterator = self.subreddit(name).hot
        else:
            iterator = self.multireddit(redditor=multireddit_owner, name=name).hot

        sorting = sorting.lower()

        args = []
        kwargs = dict(limit=limit)

        if sorting in (Sorting.TOP, Sorting.timeframe.DAY):
            iterator = self.subreddit(name).top if not multireddit_owner else self.multireddit(redditor=multireddit_owner, name=name).top
            args = [Sorting.timeframe.DAY]
        elif sorting == Sorting.NEW:
            iterator = self.subreddit(name).new if not multireddit_owner else self.multireddit(redditor=multireddit_owner, name=name).new
        elif sorting == Sorting.timeframe.WEEK:
            iterator = self.subreddit(name).top if not multireddit_owner else self.multireddit(redditor=multireddit_owner, name=name).top
            args = [Sorting.timeframe.WEEK]
        elif sorting == Sorting.timeframe.MONTH:
            iterator = self.subreddit(name).top if not multireddit_owner else self.multireddit(redditor=multireddit_owner, name=name).top
            args = [Sorting.timeframe.MONTH]
        elif sorting == Sorting.timeframe.ALL:
            iterator = self.subreddit(name).top if not multireddit_owner else self.multireddit(redditor=multireddit_owner, name=name).top
            args = [Sorting.timeframe.ALL]

        for i, submission in enumerate(iterator(*args, **kwargs)):
            if not hasattr(submission, 'current_position'):
                submission.current_position = i + 1

            yield submission

    def iter_top(self, name, limit, period='day'):
        for submission in self.subreddit(name).top(period, limit=limit):
            yield submission

    def multi_subreddits(self, redditor, name):
        return [s.display_name for s in self.multireddit(redditor, name).subreddits]

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


