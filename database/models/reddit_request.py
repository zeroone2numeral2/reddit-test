import datetime

import peewee

from database import db
from .subreddit import Subreddit


class RedditRequest(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    subreddit: Subreddit = peewee.ForeignKeyField(Subreddit, backref='reddit_requests', on_delete='NO ACTION')
    subreddit_name = peewee.CharField(null=True)  # this is just to make search easier
    account_name = peewee.CharField(null=True)
    client_name = peewee.CharField(null=True)
    request_datetime_utc = peewee.DateTimeField(null=True)

    class Meta:
        table_name = 'reddit_requests'
        database = db

    @classmethod
    def delete_old(cls, days=31):
        query = cls.delete().where(cls.request_datetime_utc < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
        return query.execute()  # returns the number of deleted rows

    def __repr__(self):
        return '<RedditRequest row {}: [{}][{}][dt:{}]>'.format(self.id, self.subreddit.name, self.subreddit.id, self.request_datetime_utc)
