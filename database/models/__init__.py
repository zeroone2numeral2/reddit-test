import logging

from .channel import Channel
from .subreddit import Subreddit
from .post import Post
from .post_resume import PostResume
from .ignored import Ignored
from .job import Job
from .subreddit_job import SubredditJob
from .reddit_request import RedditRequest
from .initial_top_post import InitialTopPost
from .style import Style
from .setting import Setting
from .flair import Flair

from database import db

logger = logging.getLogger(__name__)


def create_tables():
    with db:
        db.drop_tables([Ignored])
        db.create_tables([
            Channel,
            Subreddit,
            Post,
            PostResume,
            Job,
            SubredditJob,
            RedditRequest,
            InitialTopPost,
            Style,
            Setting,
            Flair
        ])
