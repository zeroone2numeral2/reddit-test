import datetime
from typing import TypeVar, Type

import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from .channel import Channel
from .style import Style
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
    channel: Channel = peewee.ForeignKeyField(Channel, backref='subreddits', on_delete='RESTRICT', null=True)
    # PROPERTIES THAT DICTATE WHETHER TO POST OR NOT AT A GIVEN TIME
    enabled = peewee.BooleanField(default=True)
    last_post_datetime = peewee.DateTimeField(null=True)
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency)  # in minutes
    quiet_hours_demultiplier = peewee.FloatField(null=False, default=1.0)  # 0 -> do not post during quiet hours, 1 -> same frequency as normal period
    quiet_hours_start = peewee.IntegerField(null=True, default=21)
    quiet_hours_end = peewee.IntegerField(null=True, default=6)
    # HOW TO FETCH SUBMISSIONS
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    limit = peewee.IntegerField(null=True, default=25)
    number_of_posts = peewee.IntegerField(default=1)
    # PER-RECORD STYLE
    style: Style = peewee.ForeignKeyField(Style, backref='subreddits', on_delete='RESTRICT', null=True)
    template_override = peewee.CharField(null=True)  # when set, will be used instead of any of the style's templates
    force_text = peewee.BooleanField(default=False, null=True)  # when True, submissions will be always sent as text
    respect_external_content_flag = peewee.BooleanField(default=False, null=True)  # will mainly be used to decide which template to use
    youtube_download = peewee.BooleanField(default=False)
    youtube_download_max_duration = peewee.IntegerField(default=180)
    # MISC
    added = peewee.DateTimeField(default=datetime.datetime.utcnow)
    is_multireddit = peewee.BooleanField(default=False)
    multireddit_owner = peewee.CharField(null=True)
    test = peewee.BooleanField(default=False)
    reddit_account = peewee.CharField(null=True)  # if set, we will use this account and its least used client to preform request for the subreddit
    reddit_client = peewee.CharField(null=True)  # if set, we will use this client to preform request for the subreddit
    # FILTERS
    ignore_stickied = peewee.BooleanField(default=True)
    min_score = peewee.IntegerField(null=True)
    ignore_if_newer_than = peewee.IntegerField(null=True)  # in minutes
    ignore_if_older_than = peewee.IntegerField(default=3 * 24 * 60, null=True)  # in minutes
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

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.id, self.name)

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

    def channel_username(self, default=None):
        if not self.channel or not self.channel.username:
            return default

        return self.channel.username

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

    @property
    def r_name(self):
        return '/r/{}'.format(self.name)

    @property
    def r_name_with_id(self):
        return '[{}] /r/{}'.format(self.id, self.name)

    @property
    def ch_title(self):
        if not self.channel:
            return 'none'

        return self.channel.title

    def to_dict(self):
        return model_to_dict(self)

    @classmethod
    def fetch(cls: Type[S], name) -> [S, None]:
        try:
            return cls.get(cls.name ** name)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def get_safe(cls: Type[S], *args, **kwargs) -> [S, None]:
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
            name_filter_lower = name_filter.lower()
            return [sub for sub in subs if name_filter_lower in sub.name.lower()]
    
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

    def set_default_style(self):
        self.style = Style.get_default()
        self.save()

    @classmethod
    def using_style(cls, style: Style):
        rows = (
            cls.select()
            .where(cls.style == style)
        )

        if not rows:
            return None

        return [row for row in rows]

    def template_has_hashtag(self):
        if self.template_override and '#{subreddit}' in self.template_override:
            return True

        if self.style.template and '#{subreddit}' in self.style.template:
            return True

        if self.style.template_no_url and '#{subreddit}' in self.style.template_no_url:
            return True

        if self.style.template_caption and '#{subreddit}' in self.style.template_caption:
            return True

        return False
