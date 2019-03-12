import logging

from database import db
from .models import Channel
from .models import Subreddit
from .models import Post

logger = logging.getLogger(__name__)


def create_tables():
    with db:
        db.create_tables([Channel, Subreddit, Post])


logger.info('initializing database...')
create_tables()
