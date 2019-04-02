import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .subreddit import Subreddit
from .channel import Channel


class PostResume(peewee.Model):
    submission_id = peewee.CharField(null=False)
    subreddit = peewee.ForeignKeyField(Subreddit, backref='posts')
    channel = peewee.ForeignKeyField(Channel, backref='posts')
    message_id = peewee.IntegerField(null=True)
    posted_at = peewee.DateTimeField(null=True)

    class Meta:
        table_name = 'resume_posts'
        database = db
        primary_key = peewee.CompositeKey('submission_id', 'subreddit')
        indexes = (
            (('submission_id', 'subreddit_id', 'channel'), True),
        )

    def __repr__(self):
        return '<ResumePost: submission id {}, subreddit id {}, channel id {}>'.format(
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

