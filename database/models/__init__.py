import logging

from .channel import Channel
from .subreddit import Subreddit
from .post import Post
from .post_resume import PostResume
from .ignored import Ignored

from database import db

logger = logging.getLogger(__name__)


def create_tables():
    with db:
        db.create_tables([Channel, Subreddit, Post, Ignored])
