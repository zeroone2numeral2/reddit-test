import datetime

from peewee import fn

from ..models import Subreddit
from ..models import SubredditJob


def average_daily_posts(subreddit: Subreddit, days=7) -> [float, bool]:
    delta: datetime = datetime.datetime.utcnow() - datetime.timedelta(hours=days * 24)
    query = (
        SubredditJob.select(fn.SUM(SubredditJob.posted_messages).alias('day_total'))
        .where(SubredditJob.start > delta, SubredditJob.posted_messages.is_null(False), SubredditJob.subreddit == subreddit)
        .group_by(fn.day_part(SubredditJob.start))
    )

    # we use this query to check whether we have data PREVIOUS to the time delta requested
    # if yes, the function must return that the average data provided is originated on a partial dataset (that is,
    # data is from less days than requested)
    partial = not SubredditJob.select().where(SubredditJob.subreddit == subreddit, SubredditJob.start < delta).exists()

    if not query:
        return 0, partial

    total = 0
    i = 0
    for row in query:
        total += row.day_total
        i += 1

    avg = total / i

    if avg % 1 == 0.0:
        return int(avg), partial
    else:
        return round(avg, 1), partial


def top_fontpage_depth(subreddit: Subreddit, days=7):
    delta: datetime = datetime.datetime.utcnow() - datetime.timedelta(hours=days * 24)
    query = (
        SubredditJob.select(SubredditJob.frontpage_max_depth.alias('depth'), fn.COUNT(SubredditJob.frontpage_max_depth).alias('times'))
        .where(SubredditJob.start > delta, SubredditJob.subreddit == subreddit, SubredditJob.frontpage_max_depth.is_null(False))
        .group_by(SubredditJob.frontpage_max_depth)
        .order_by(SubredditJob.frontpage_max_depth.desc())
    ).dicts()

    if not query:
        return

    return list(query)
