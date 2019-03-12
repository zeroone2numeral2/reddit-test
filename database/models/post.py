import peewee
from playhouse.shortcuts import model_to_dict

from ..database import db
from .channel import Channel


class Post(peewee.Model):
    submission_id = peewee.CharField(null=False)
    subreddit_id = peewee.CharField(null=False)
    channel = peewee.ForeignKeyField(Channel, backref='posts')
    message_id = peewee.IntegerField(null=False)
    posted_at = peewee.DateTimeField(null=False)

    class Meta:
        table_name = 'posts'
        database = db
        primary_key = peewee.CompositeKey('submission_id', 'subreddit_id')
        indexes = (
            (('submission_id', 'subreddit_id', 'channel'), True),
        )

    def __repr__(self):
        return '<Post: submission id {}, subreddit id {}, channel id {}>'.format(
            self.submission_id,
            self.subreddit_id,
            self.channel.channel_id
        )
