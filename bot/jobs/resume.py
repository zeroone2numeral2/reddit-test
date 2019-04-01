import logging
import time
from pprint import pprint

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u
from utilities import d
from database.models import Subreddit
from database.models import Post
from reddit import reddit
from reddit import Sorting
from reddit import Sender
from bot import Jobs
from ..jobregistration import RUNNERS
from config import config

logger = logging.getLogger(__name__)

READABLE_TIME_FORMAT = '%d/%m/%Y %H:%M:%S'


#@Jobs.add(RUNNERS.run_repeating, interval=10*60, first=0, name='resume_job')
@d.logerrors
@d.log_start_end_dt
def check_daily_resume(bot, job):
    pass
