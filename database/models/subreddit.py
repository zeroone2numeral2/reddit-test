import peewee
from playhouse.shortcuts import model_to_dict

from ..database import db
from .channel import Channel
from utilities import u
from config import config


DATETIME_ORMATS = [
    # see http://docs.peewee-orm.com/en/latest/peewee/api.html#DateTimeField
    '%Y-%m-%d %H:%M:%S.%f',  # year-month-day hour-minute-second.microsecond
    '%Y-%m-%d %H:%M:%S.%f+00:00',  # year-month-day hour-minute-second.microsecond - UTC format
    '%Y-%m-%d %H:%M:%S',  # year-month-day hour-minute-second
    '%Y-%m-%d',  # year-month-day
]


class Subreddit(peewee.Model):
    subreddit_id = peewee.CharField(primary_key=True, index=True)
    name = peewee.CharField(null=False, default=0)
    channel = peewee.ForeignKeyField(Channel, backref='posts')
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency, help_text='Max frequency in minutes')
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    min_score = peewee.IntegerField(null=True)
    added = peewee.DateTimeField(default=u.now)
    enabled = peewee.BooleanField(default=True)
    template = peewee.CharField(null=True)
    send_images = peewee.BooleanField(default=True)
    images_as_file = peewee.BooleanField(default=False)
    images_only = peewee.BooleanField(default=False)
    webpage_preview = peewee.BooleanField(default=True)

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.subreddit_id, self.name)

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)
