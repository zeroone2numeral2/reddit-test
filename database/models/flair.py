import datetime

import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class Flair(peewee.Model):
    flair_id = peewee.IntegerField(primary_key=True, index=True)
    subreddit_name = peewee.CharField(null=False)
    flair = peewee.CharField(null=False)
    last_seen_utc = peewee.DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'flairs'
        database = db

    def to_dict(self):
        return model_to_dict(self)
