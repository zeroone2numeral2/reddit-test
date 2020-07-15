import datetime

import peewee

from database import db
from .subreddit import Subreddit
from .channel import Channel


class PostResume(peewee.Model):
    submission_id = peewee.CharField(null=False, primary_key=True)
    subreddit = peewee.ForeignKeyField(Subreddit, backref='resume_posts')
    channel = peewee.ForeignKeyField(Channel, backref='resume_posts')
    message_id = peewee.IntegerField(null=True)
    posted_at = peewee.DateTimeField(null=True)
    sent_message = peewee.CharField(null=True)

    class Meta:
        table_name = 'resume_posts'
        database = db
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

    @classmethod
    def delete_old(cls, days=31):
        query = cls.delete().where(cls.posted_at < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
        return query.execute()  # returns the number of deleted rows

