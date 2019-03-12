import logging

from database import db
from .models import Post

logger = logging.getLogger(__name__)


def create_tables():
    with db:
        db.create_tables([Post])


logger.info('initializing database...')
create_tables()
