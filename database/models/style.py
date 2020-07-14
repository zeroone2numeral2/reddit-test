import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class Style(peewee.Model):
    style_id = peewee.IntegerField(primary_key=True, index=True)
    name = peewee.CharField(null=False)
    created = peewee.DateTimeField(null=True)
    updated = peewee.DateTimeField(null=True)
    # actual style fields
    template = peewee.CharField(null=True)
    template_no_url = peewee.CharField(null=True)
    url_button = peewee.BooleanField(default=False)
    url_button_template = peewee.CharField(null=True)
    comments_button = peewee.BooleanField(default=False)
    comments_button_template = peewee.CharField(null=True)
    send_medias = peewee.BooleanField(default=True)
    webpage_preview = peewee.BooleanField(default=True)

    class Meta:
        table_name = 'styles'
        database = db

    def __repr__(self):
        return '<Style {}: {}>'.format(self.style_id, self.name)

    def to_dict(self):
        return model_to_dict(self)
