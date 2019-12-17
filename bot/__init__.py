import database.database   # we need it to initialize the package as soon as possible
from .bot import RedditBot
from utilities import utilities
from .jobs.post import check_posts
from .jobs.resume import check_daily_resume
from config import config


bot = RedditBot(token=config.telegram.token, use_context=True, workers=1)


def main():
    utilities.load_logging_config('logging.json')

    bot.import_handlers(r'bot/plugins/')
    bot.job_queue.run_repeating(check_daily_resume, interval=config.jobs.resume_job.interval * 60, first=config.jobs.resume_job.first * 60, name='resume_job')
    bot.job_queue.run_repeating(check_posts, interval=config.jobs.posts_job.interval * 60, first=config.jobs.posts_job.first * 60, name='posts_job')

    bot.run(clean=True)


if __name__ == '__main__':
    main()
