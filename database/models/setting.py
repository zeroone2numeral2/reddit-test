import datetime

import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class Setting(peewee.Model):
    setting_id = peewee.IntegerField(primary_key=True, index=True)
    key = peewee.CharField(null=False, unique=True)
    value = peewee.IntegerField(default=0)

    class Meta:
        table_name = 'settings'
        database = db

    def to_dict(self):
        return model_to_dict(self)

    @classmethod
    def get_key(cls, key, create_if_missing=True):
        key = key.lower()

        try:
            return cls.get(cls.key == key)
        except peewee.DoesNotExist:
            # raise an error if there is no row with that key, or create it
            if not create_if_missing:
                raise peewee.InternalError('no key "{}" found'.format(key))

            setting = cls.create(key=key)

            return setting


