import peewee
from playhouse.shortcuts import model_to_dict

from database import db


class Style(peewee.Model):
    style_id = peewee.IntegerField(primary_key=True, index=True)
    name = peewee.CharField(null=False, unique=True)
    created = peewee.DateTimeField(null=True)
    updated = peewee.DateTimeField(null=True)
    # actual style fields
    template = peewee.CharField(null=True)
    template_no_url = peewee.CharField(null=True)  # when the submission doesn't have an url
    template_caption = peewee.CharField(null=True)  # when we are going to send a media with a caption
    template_resume = peewee.CharField(null=True)
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

    @classmethod
    def default(cls):
        try:
            return cls.get(cls.name == 'default')
        except peewee.DoesNotExist:
            # raise an error if there is no default style
            raise peewee.InternalError('no default Style found')
