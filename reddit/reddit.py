import datetime

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
            for submission in self.subreddit(name).top('all', limit=1):
                return str(submission.subreddit)  # save the correct name
        except Redirect:
            return False

    def get_submissions(self, subreddit, sorting='hot', limit=config.praw.submissions_limit):
        result = list()
        for submission in self.iter_submissions(subreddit, sorting, limit):
            created_utc_dt = datetime.datetime.utcfromtimestamp(submission.created_utc)

            result.append(dict(
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
