import peewee

from database import db
from .subreddit import Subreddit


class SubredditJob(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    subreddit: Subreddit = peewee.ForeignKeyField(Subreddit, backref='subreddit_jobs', on_delete='NO ACTION')
    subreddit_name = peewee.CharField(null=True)  # this is just to make search easier
    job_name = peewee.CharField(null=True)
    start = peewee.DateTimeField(null=True)
    end = peewee.DateTimeField(null=True)
    duration = peewee.IntegerField(null=True)
    posted_messages = peewee.IntegerField(null=True)
    uploaded_bytes = peewee.IntegerField(null=True)

    class Meta:
        table_name = 'subreddit_jobs'
        database = db

    def __repr__(self):
        return '<SubredditJob row {}: [{}][{}][start:{}]>'.format(self.id, self.subreddit.name, self.subreddit.id, self.start)

