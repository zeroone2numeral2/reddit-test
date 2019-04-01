import datetime

import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .channel import Channel
from const import DEFAULT_TEMPLATE
from const import DEFAULT_ANNOUNCEMENT_TEMPLATE
from config import config

DATETIME_ORMATS = [
    # see http://docs.peewee-orm.com/en/latest/peewee/api.html#DateTimeField
    '%Y-%m-%d %H:%M:%S.%f',  # year-month-day hour-minute-second.microsecond
    '%Y-%m-%d %H:%M:%S.%f+00:00',  # year-month-day hour-minute-second.microsecond - UTC format
    '%Y-%m-%d %H:%M:%S',  # year-month-day hour-minute-second
    '%Y-%m-%d',  # year-month-day
]


class Resume(peewee.Model):
    subreddit_id = peewee.CharField(primary_key=True, index=True)
    name = peewee.CharField(null=False)
    channel = peewee.ForeignKeyField(Channel, backref='posts', on_delete='NO ACTION')
    hour = peewee.IntegerField(default=22)
    frequency = peewee.CharField(default='day')
    number_of_posts = peewee.IntegerField(default=3)
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    added = peewee.DateTimeField(default=datetime.datetime.utcnow)
    enabled = peewee.BooleanField(default=True)
    template = peewee.CharField(null=True, default=DEFAULT_TEMPLATE)
    announcement_template = peewee.CharField(null=True, default=DEFAULT_ANNOUNCEMENT_TEMPLATE)
    send_medias = peewee.BooleanField(default=True)
    webpage_preview = peewee.BooleanField(default=True)
    test = peewee.BooleanField(default=False)
    # FILTERS
    ignore_stickied = peewee.BooleanField(default=True)
    images_only = peewee.BooleanField(default=False)
    min_score = peewee.IntegerField(default=1)
    allow_nsfw = peewee.BooleanField(default=True, null=True)

    class Meta:
        table_name = 'resumes'
        database = db

    def __repr__(self):
        return '<Resume {}: {}>'.format(self.subreddit_id, self.name)

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
                .order_by(cls.name)
        )

        return [sub for sub in subs]

    @classmethod
    def subreddit_with_channel(cls, channel):
        try:
            cls.get(cls.channel == channel)
            return True
        except peewee.DoesNotExist:
            return False
