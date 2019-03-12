import peewee
from playhouse.shortcuts import model_to_dict

from ..database import db
from config import config


class Subreddit(peewee.Model):
    subreddit_id = peewee.CharField(primary_key=True, index=True)
    name = peewee.CharField(null=False)
    max_frequency = peewee.IntegerField(default=config.submissions.default_max_frequency, help_text='Max frequency in minutes')
    last_posted_submission_dt = peewee.DateTimeField(null=True)
    link_preview = peewee.BooleanField(default=True)
    sorting = peewee.CharField(default=config.submissions.default_sorting)
    min_score = peewee.IntegerField(null=True)

    class Meta:
        table_name = 'subreddits'
        database = db

    def __repr__(self):
        return '<Subreddit {}: {}>'.format(self.subreddit_id, self.name)
