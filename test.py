import logging

from telegram import Bot

from reddit import reddit
from reddit import Sender
from database.models import Subreddit
from utilities import u
from config import config

logger = logging.getLogger(__name__)
bot = Bot(config.telegram.token)

SUB_NAME = 'ricardo_test'

u.load_logging_config(config.logging.config, config.logging.filepath)


IGNORE_SUBMISSIONS = [
    'b3zaqd',  # vreddit with sound
    'b3z78n',  # direct mp4 url
]


def main():
    logger.info('starting...')
    rtest = Subreddit.get(Subreddit.name == 'ricardo_test')
    
    for submission in reddit.iter_submissions(SUB_NAME, 'hot', limit=100):
        if submission.id in IGNORE_SUBMISSIONS:
            continue
        
        logger.info('')
        logger.info('')
        logger.info('')
        logger.info('TITLE: %s (%s)', submission.title, submission.id)
        
        sender = Sender(bot, rtest, submission)
        
        if sender.test_filters():
            logger.info('submission passed filters')
        else:
            logger.info('submission does not pass filters')
        
        sender.post()


if __name__ == '__main__':
    main()
