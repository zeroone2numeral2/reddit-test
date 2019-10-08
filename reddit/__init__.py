from .sender import Sender
from .sender_resume import SenderResume
from .sortings import Sorting
from .reddit import Reddit
from config import config


reddit = Reddit(
    client_id=config.praw.client_id,
    client_secret=config.praw.client_secret,
    user_agent=config.praw.user_agent,
    username=config.praw.username,
    password=config.praw.password
)
