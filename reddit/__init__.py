import praw

from .sender import Sender
from .sortings import Sorting
from config import config


reddit = praw.Reddit(
    client_id=config.praw.client_id,
    client_secret=config.praw.client_secret,
    user_agent=config.praw.user_agent
)
