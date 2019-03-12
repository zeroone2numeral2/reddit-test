import peewee
from playhouse.shortcuts import model_to_dict

from ..database import db


class Channel(peewee.Model):
    channel_id = peewee.IntegerField(primary_key=True, index=True)
    title = peewee.CharField(null=False)
    username = peewee.CharField(null=True)
    template = peewee.CharField(null=True)
    send_images = peewee.BooleanField(default=False)
    added = peewee.DateTimeField(null=False)
    enabled = peewee.BooleanField(default=True)

    class Meta:
        table_name = 'channels'
        database = db

    def __repr__(self):
        return '<Channel {}: {}>'.format(self.channel_id, self.title)
