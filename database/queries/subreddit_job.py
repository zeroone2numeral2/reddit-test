import datetime

from peewee import fn

from ..models import Subreddit
from ..models import SubredditJob


def average_daily_posts(subreddit: Subreddit, hours=7*24) -> int:
    delta: datetime = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
    query = (
        SubredditJob.select(fn.SUM(SubredditJob.posted_messages).alias('day_total'))
        .where(SubredditJob.start > delta, SubredditJob.posted_messages.is_null(False), SubredditJob.subreddit == subreddit)
        .group_by(fn.day_part(SubredditJob.start))
    )

    if not query:
        return 0

    total = 0
    i = 0
    for row in query:
        total += row.day_total
        i += 1

    avg = total / i

    if avg % 1 == 0.0:
        return int(avg)
    else:
        return round(avg, 1)
