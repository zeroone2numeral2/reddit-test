import datetime

import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class Channel(peewee.Model):
    channel_id = peewee.IntegerField(primary_key=True, index=True)
    title = peewee.CharField(null=False)
    username = peewee.CharField(null=True)
    added = peewee.DateTimeField(default=datetime.datetime.utcnow)
    invite_link = peewee.CharField(null=True)

    class Meta:
        table_name = 'channels'
        database = db

    def __repr__(self):
        return '<Channel {}: {}>'.format(self.channel_id, self.title)

    @classmethod
    def to_dict(cls):
        return model_to_dict(cls)

    @classmethod
    def exists(cls, channel_id):
        try:
            return bool(cls.get(cls.channel_id == channel_id))
        except peewee.DoesNotExist:
            return False

    @classmethod
    def create_from_chat(cls, chat):
        cls.create(
            channel_id=chat.id,
            title=chat.title,
            username=chat.username,
            invite_link=chat.invite_link
        )

    @classmethod
    def update_channel(cls, chat):
        channel = cls.get(cls.channel_id == chat.id)

        channel.title = chat.title
        channel.username = chat.username
        channel.invite_link = chat.invite_link
        channel.save()

    @classmethod
    def get_list(cls):
        all_channels = (
            cls.select()
            .order_by(peewee.fn.lower(cls.title))
        )

        return_list = list()
        for channel in all_channels:
            channel_id = str(channel.channel_id).replace('-100', '')
            return_list.append('{}. {}'.format(channel_id, channel.title))

        return return_list

    @classmethod
    def safe_get(cls, channel_id):
        try:
            return cls.get(cls.channel_id == channel_id)
        except peewee.DoesNotExist:
            return None
