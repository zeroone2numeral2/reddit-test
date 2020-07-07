import database.database   # we need it to initialize the package as soon as possible
from .logging import logging_config
from .bot import RedditBot
from .jobs.stream import check_posts
from .jobs.resume import check_daily_resume
from config import config


mainbot = RedditBot(token=config.telegram.token, use_context=True, workers=1)


def main():
    # load_logging_config('logging.json')

    mainbot.import_handlers(r'bot/plugins/')
    mainbot.job_queue.run_repeating(check_daily_resume, interval=config.jobs.resume.interval * 60, first=config.jobs.resume.first * 60, name='resume')
    mainbot.job_queue.run_repeating(check_posts, interval=config.jobs.stream.interval * 60, first=config.jobs.stream.first * 60, name='stream')

    mainbot.run(clean=True)


if __name__ == '__main__':
    main()
