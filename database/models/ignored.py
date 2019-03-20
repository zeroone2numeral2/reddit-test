import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .subreddit import Subreddit


class Ignored(peewee.Model):
    submission_id = peewee.CharField(null=False)
    subreddit = peewee.ForeignKeyField(Subreddit, backref='ignored')
    ignored_at = peewee.DateTimeField(null=True)
    reason = peewee.CharField(null=True)

    class Meta:
        table_name = 'ignored'
        database = db
        primary_key = peewee.CompositeKey('submission_id', 'subreddit')
        indexes = (
            (('submission_id', 'subreddit_id'), True),
        )

    def __repr__(self):
        return '<Ignored: submission id {}, subreddit id {}>'.format(self.submission_id, self.subreddit_id)

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

