import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .subreddit import Subreddit


class Ignored(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    submission_id = peewee.CharField(null=False)
    subreddit = peewee.ForeignKeyField(Subreddit, backref='ignored')
    ignored_at = peewee.DateTimeField(null=True)
    reason = peewee.CharField(null=True)

    class Meta:
        table_name = 'ignored'
        database = db

    def __repr__(self):
        return '<Ignored: submission id {}, subreddit id {}>'.format(self.submission_id, self.subreddit_id)

    @classmethod
    def ignored(cls, submission_id, subreddit_id):
        try:
            cls.get(cls.submission_id == submission_id, cls.subreddit_id == subreddit_id)
            return True
        except peewee.DoesNotExist:
            return False
    

