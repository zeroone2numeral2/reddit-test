import datetime
from typing import TypeVar, Type

import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .channel import Channel
from const import *
from config import config


DATETIME_ORMATS = [
    # see http://docs.peewee-orm.com/en/latest/peewee/api.html#DateTimeField
    '%Y-%m-%d %H:%M:%S.%f',  # year-month-day hour-minute-second.microsecond
    '%Y-%m-%d %H:%M:%S.%f+00:00',  # year-month-day hour-minute-second.microsecond - UTC format
    '%Y-%m-%d %H:%M:%S',  # year-month-day hour-minute-second
    '%Y-%m-%d',  # year-month-day
]

S = TypeVar('S', bound='Subreddit')


class Subreddit(peewee.Model):
    subreddit_id = peewee.CharField(primary_key=True, index=True)
    name = peewee.CharField(null=False, default=0)
    channel = peewee.ForeignKeyField(Channel, backref='posts', on_delete='NO ACTION')
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency, help_text='Max frequency in minutes')
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    added = peewee.DateTimeField(default=datetime.datetime.utcnow)
    enabled = peewee.BooleanField(default=True)
    template = peewee.CharField(null=True, default=DEFAULT_TEMPLATE)
    send_medias = peewee.BooleanField(default=True)
    webpage_preview = peewee.BooleanField(default=True)
    # quiet_hours_demultiplier: 0 -> do not post during quiet hours, 1 -> same frequency as normal period
    quiet_hours_demultiplier = peewee.FloatField(null=True, default=1.0)
    limit = peewee.IntegerField(null=True, default=config.praw.submissions_limit)
    quiet_hours_start = peewee.IntegerField(null=True, default=config.quiet_hours.start)
    quiet_hours_end = peewee.IntegerField(null=True, default=config.quiet_hours.end)
    number_of_posts = peewee.IntegerField(default=1)
    test = peewee.BooleanField(default=False)
    # FILTERS
    ignore_stickied = peewee.BooleanField(default=True)
    min_score = peewee.IntegerField(null=True)
    ignore_if_newer_than = peewee.IntegerField(null=True)
    allow_nsfw = peewee.BooleanField(default=True, null=True)
    hide_spoilers = peewee.BooleanField(default=False, null=True)
    medias_only = peewee.BooleanField(default=False, null=True)
    # RESUME FIELDS
    enabled_resume = peewee.BooleanField(default=False)
    hour = peewee.IntegerField(default=22)
    weekday = peewee.IntegerField(default=5)  # 0-6, from Monday to Sunday
    frequency = peewee.CharField(default='day')
    template_resume = peewee.CharField(null=True)
    resume_last_posted_submission_dt = peewee.DateTimeField(null=True)

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.subreddit_id, self.name)

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

    @classmethod
    def fetch(cls: Type[S], name) -> S:
        try:
            return cls.get(cls.name ** name)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def set_field(cls, field, value):
        setattr(cls, field, value)

    @classmethod
    def get_list(cls):
        subs = (
            cls.select()
            # .order_by(peewee.fn.lower(cls.name))
            .order_by(cls.added)
        )
        
        return [sub for sub in subs]
    
    @classmethod
    def subreddit_with_channel(cls, channel):
        try:
            cls.get(cls.channel == channel)
            return True
        except peewee.DoesNotExist:
            return False

    @classmethod
    def subreddits_with_jobs(cls):
        subs = (
            cls.select()
            .order_by(cls.name)
        )

        return [(sub.name, sub.enabled, sub.enabled_resume) for sub in subs]

    @classmethod
    def get_invite_links(cls):
        rows = (
            Channel.select(
                Channel.channel_id,
                Channel.title,
                Channel.invite_link,
                peewee.fn.GROUP_CONCAT(cls.name, ', ').coerce(False).alias('subreddits')
            )
            .join(cls)
            .where((cls.enabled == True) | (cls.enabled_resume == True))
            .group_by(Channel.channel_id)
            .order_by(peewee.fn.lower(Channel.title))
            .dicts()
        )

        return [{**row, 'subreddits': row['subreddits'].split(', ')} for row in rows]

    @classmethod
    def get_channels(cls):
        rows = (
            Channel.select(
                Channel.channel_id,
                Channel.title,
                Channel.invite_link,
                Channel.added,
                peewee.fn.GROUP_CONCAT(cls.name, ', ').coerce(False).alias('subreddits')
            )
            .join(cls)
            .where((cls.enabled == True) | (cls.enabled_resume == True))
            .group_by(Channel.channel_id)
            # .order_by(peewee.fn.lower(Channel.title))
            .order_by(Channel.added)
            .dicts()
        )

        return [{**row, 'subreddits': row['subreddits'].split(', ')} for row in rows]
