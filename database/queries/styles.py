import peewee

from ..models import Style
from ..models import Subreddit


def is_used(style: Style):
    return bool(Subreddit.select().where(Subreddit.style == style))
