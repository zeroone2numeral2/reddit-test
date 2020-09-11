import datetime

import peewee
from playhouse.shortcuts import model_to_dict

from database import db
from const import DEFAULT_TEMPLATE


class Style(peewee.Model):
    style_id = peewee.IntegerField(primary_key=True, index=True)
    name = peewee.CharField(null=False, unique=True)
    created = peewee.DateTimeField(null=True)
    updated = peewee.DateTimeField(null=True)
    default = peewee.BooleanField(default=False)
    # actual style fields
    template = peewee.CharField(null=True)
    template_no_url = peewee.CharField(null=True)  # when the submission doesn't have an url
    template_caption = peewee.CharField(null=True)  # when we are going to send a media with a caption
    template_no_url_for_captions = peewee.BooleanField(default=True)  # decides whether to use template_no_url as fallback when template_caption is not set
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
    def get_default(cls, create_if_missing=True):
        try:
            return cls.get(cls.default == True)
        except peewee.DoesNotExist:
            # raise an error if there is no default style
            if not create_if_missing:
                raise peewee.InternalError('no default Style found')

            now = datetime.datetime.utcnow()
            new_default = cls.create(
                name='default_{}'.format(now.strftime('%Y%m%d_%H%M%S')),
                default=True,
                template=DEFAULT_TEMPLATE,
                created=now,
                updated=now
            )

            return new_default

    @classmethod
    def by_name(cls, name):
        try:
            return cls.get(cls.name == name.lower())
        except peewee.DoesNotExist:
            return None

    @classmethod
    def get_list(cls, name_filter=None):
        styles = (
            cls.select()
            .order_by(cls.name)
        )

        if not name_filter:
            return [sub for sub in styles]
        else:
            name_filter = name_filter.lower()
            return [sub for sub in styles if name_filter in sub.name.lower()]

    @classmethod
    def no_default(cls):
        query = cls.update(default=False).where(cls.default == True)
        return query.execute()

    def make_default(self):
        Style.no_default()
        self.default = True
        self.save()

    def update_time(self, dt_object: datetime, save=True):
        self.updated = dt_object
        if save:
            self.save()

    def field_exists(self, key):
        try:
            getattr(self, key)
            return True
        except AttributeError:
            return False
