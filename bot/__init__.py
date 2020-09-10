import sys

import database.database   # we need it to initialize the package as soon as possible
from .logging import logging_config
from .bot import RedditBot
from .bot import DummyContext
from .jobs.stream import check_posts, stream_job
from .jobs.resume import check_daily_resume
from config import config

from apscheduler.schedulers.background import BackgroundScheduler


mainbot = RedditBot(token=config.telegram.token, use_context=True, workers=1)

scheduler = BackgroundScheduler(daemon=True)


def main():
    # load_logging_config('logging.json')

    mainbot.import_handlers(r'bot/plugins/')
    # mainbot.job_queue.run_repeating(check_daily_resume, interval=config.jobs.resume.interval * 60, first=config.jobs.resume.first * 60, name='resume')
    mainbot.job_queue.run_repeating(check_posts, interval=config.jobs.stream.interval * 60, first=config.jobs.stream.first * 60, name='stream')

    # context = DummyContext(mainbot, 'stream')
    # scheduler.add_job(stream_job, id='stream', kwargs=dict(context=context))
    # scheduler.start()

    mainbot.run(clean=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        scheduler.shutdown()  # does not interrupt any currently running job
        sys.exit()
