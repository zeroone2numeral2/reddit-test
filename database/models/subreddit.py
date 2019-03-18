import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .channel import Channel
from const import DEFAULT_TEMPLATE
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
    channel = peewee.ForeignKeyField(Channel, backref='posts', on_delete='NO ACTION')
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency, help_text='Max frequency in minutes')
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    added = peewee.DateTimeField(default=u.now)
    enabled = peewee.BooleanField(default=True)
    template = peewee.CharField(null=True, default=DEFAULT_TEMPLATE)
    send_images = peewee.BooleanField(default=True)
    images_as_file = peewee.BooleanField(default=False)
    webpage_preview = peewee.BooleanField(default=True)
    follow_quiet_hours = peewee.BooleanField(null=True, default=True)
    limit = peewee.IntegerField(null=True, default=config.praw.submissions_limit)
    # FILTERS
    ignore_stickied = peewee.BooleanField(default=True)
    images_only = peewee.BooleanField(default=False)
    min_score = peewee.IntegerField(null=True)
    ignore_if_newer_then = peewee.IntegerField(null=True)

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.subreddit_id, self.name)

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

    @classmethod
    def fetch(cls, name):
        try:
            return cls.get(cls.name ** name)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def set_field(cls, field, value):
        setattr(cls, field, value)

    @classmethod
    def get_list(cls):
        return_list = list()
        
        subs = (
            cls.select()
        )
        
        return [sub for sub in subs]
