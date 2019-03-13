import praw
from prawcore.exceptions import Redirect


class Reddit(praw.Reddit):
    def __init__(self, *args, **kwargs):
        praw.Reddit.__init__(self,  *args, **kwargs)
    
    def subreddit_exists(self, name):
        try:
            for submission in self.subreddit(name).new(limit=1):
                return str(submission.subreddit)  # save the correct name
        except Redirect:
            return False
