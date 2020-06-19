from .sender import Sender
from .sender_resume import SenderResume
from .sortings import Sorting
from .reddit import Reddit
from .accounts import AccountManager
from config import config


accounts = AccountManager(config.reddit)

# reddit = Reddit(**config.praw)
reddit = accounts.default
