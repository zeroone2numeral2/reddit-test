import datetime
from typing import TypeVar, Type

import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .channel import Channel
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
    id = peewee.AutoField()
    subreddit_id = peewee.CharField(index=True)
    name = peewee.CharField(null=False, default=0)
    channel: Channel = peewee.ForeignKeyField(Channel, backref='subreddit', on_delete='NO ACTION', null=True)
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency, help_text='Max frequency in minutes')
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    added = peewee.DateTimeField(default=datetime.datetime.utcnow)
    enabled = peewee.BooleanField(default=True)
    # quiet_hours_demultiplier: 0 -> do not post during quiet hours, 1 -> same frequency as normal period
    quiet_hours_demultiplier = peewee.FloatField(null=True, default=1.0)
    limit = peewee.IntegerField(null=True, default=25)
    quiet_hours_start = peewee.IntegerField(null=True, default=21)
    quiet_hours_end = peewee.IntegerField(null=True, default=6)
    number_of_posts = peewee.IntegerField(default=1)
    is_multireddit = peewee.BooleanField(default=False)
    multireddit_owner = peewee.CharField(null=True)
    test = peewee.BooleanField(default=False)
    youtube_download = peewee.BooleanField(default=False)
    youtube_download_max_duration = peewee.IntegerField(default=180)
    reddit_account = peewee.CharField(null=True)
    reddit_client = peewee.CharField(null=True)
    # STYLE
    template = peewee.CharField(null=True)
    template_no_url = peewee.CharField(null=True)
    url_button = peewee.BooleanField(default=False)
    url_button_template = peewee.CharField(null=True)
    comments_button = peewee.BooleanField(default=False)
    comments_button_template = peewee.CharField(null=True)
    send_medias = peewee.BooleanField(default=True)
    webpage_preview = peewee.BooleanField(default=True)
    # FILTERS
    ignore_stickied = peewee.BooleanField(default=True)
    min_score = peewee.IntegerField(null=True)
    ignore_if_newer_than = peewee.IntegerField(null=True)
    allow_nsfw = peewee.BooleanField(default=True, null=True)
    hide_spoilers = peewee.BooleanField(default=False, null=True)
    medias_only = peewee.BooleanField(default=False, null=True)
    min_upvote_perc = peewee.IntegerField(default=False, null=True)
    ignore_flairless = peewee.BooleanField(default=False, null=True)
    # RESUME FIELDS
    enabled_resume = peewee.BooleanField(default=False)
    hour = peewee.IntegerField(default=22)
    weekday = peewee.IntegerField(default=5)  # 0-6, from Monday to Sunday
    frequency = peewee.CharField(default='day')
    resume_last_posted_submission_dt = peewee.DateTimeField(null=True)
    # RESUME STYLE
    template_resume = peewee.CharField(null=True)

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.subreddit_id, self.name)

    def update_from_dict(self, data: dict):
        for field, value in data.items():
            # probably slow af
            setattr(self, field, value)

        self.save()

        return self

    def channel_title(self, default='none'):
        if not self.channel:
            return default

        return self.channel.title

    def get_channel_invite_link(self, ignore_public_username=False, default=None):
        if not self.channel:
            return default

        if not self.channel.username or ignore_public_username:
            if self.channel.invite_link:
                return self.channel.invite_link
            else:
                return default
        else:
            return 'https://t.me/' + self.channel.username

    @property
    def channel_link(self):
        return self.get_channel_invite_link()

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

    @classmethod
    def fetch(cls: Type[S], name) -> [S, None]:
        try:
            return cls.get(cls.name ** name)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def get_safe(cls: Type[S], *args, **kwargs):
        try:
            return cls.get(*args, **kwargs)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def set_field(cls, field, value):
        setattr(cls, field, value)

    @classmethod
    def get_list(cls, name_filter=None):
        subs = (
            cls.select()
            # .order_by(peewee.fn.lower(cls.name))
            .order_by(cls.added)
        )

        if not name_filter:
            return [sub for sub in subs]
        else:
            return [sub for sub in subs if name_filter.lower() in sub.name.lower()]
    
    @classmethod
    def linked_to_channel(cls, channel):
        try:
            subs = (
                cls.select().
                where(cls.channel == channel)
            )

            return [sub for sub in subs]
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
                peewee.fn.GROUP_CONCAT(cls.id, ', ').coerce(False).alias('subreddits')
            )
            .join(cls)
            .where((cls.enabled == True) | (cls.enabled_resume == True))
            .group_by(Channel.channel_id)
            # .order_by(peewee.fn.lower(Channel.title))
            .order_by(Channel.added)
            .dicts()
        )

        return [{**row, 'subreddits': row['subreddits'].split(', ')} for row in rows]
