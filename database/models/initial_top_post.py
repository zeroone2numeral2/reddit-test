import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class InitialTopPost(peewee.Model):
    """This table should contain a list of top posts saved at the moment we set a
    subreddit to use the "month" or "all" sorting method. To avoid to post some old top posts for a long
    period (for example, a channel where we check daily if there's a new top post in the first 50 posts of all time
    would post for the first 50 days the current top posts), we store the top posts at the moment we set the
    sorting method, so we can make sure it's not old stuff"""

    id = peewee.AutoField()
    submission_id = peewee.CharField(null=False)
    subreddit_name = peewee.CharField(null=False)
    sorting = peewee.CharField(null=False)

    class Meta:
        table_name = 'initial_top_posts'
        database = db
        indexes = (
            (('submission_id', 'subreddit_name', 'sorting'), True),
        )

    def __repr__(self):
        return '<InitialTopPost: submission id {}, subreddit id {}, channel id {}>'.format(
            self.submission_id,
            self.subreddit_name,
            self.sorting
        )

    @classmethod
    def is_initial_top_post(cls, subreddit_name, submission_id, sorting):
        try:
            return bool(cls.get(
                cls.subreddit_name == subreddit_name,
                cls.submission_id == submission_id,
                cls.sorting == sorting
            ))
        except peewee.DoesNotExist:
            return False

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

