import peewee
from playhouse.shortcuts import model_to_dict

from ..database import db
from .channel import Channel
from .subreddit import Subreddit


class Post(peewee.Model):
    submission_id = peewee.CharField(null=False)
    subreddit = peewee.ForeignKeyField(Subreddit, backref='posts')
    channel = peewee.ForeignKeyField(Channel, backref='posts')
    message_id = peewee.IntegerField(null=False)
    posted_at = peewee.DateTimeField(null=False)

    class Meta:
        table_name = 'posts'
        database = db
        primary_key = peewee.CompositeKey('submission_id', 'subreddit')
        indexes = (
            (('submission_id', 'subreddit_id', 'channel'), True),
        )

    def __repr__(self):
        return '<Post: submission id {}, subreddit id {}, channel id {}>'.format(
            self.submission_id,
            self.subreddit_id,
            self.channel.channel_id
        )

    @classmethod
    def already_posted(cls, subreddit, submission_id):
        try:
            return bool(cls.get(cls.subreddit == subreddit, cls.submission_id == submission_id))
        except peewee.DoesNotExist:
            return False

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

