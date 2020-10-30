import datetime

from peewee import fn

from ..models import Job


def average(hours=7*24) -> [None, list]:
    delta = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    query = (
        Job.select(
            Job.name,
            fn.AVG(Job.duration).alias('avg_duration'),
            fn.AVG(Job.uploaded_bytes).alias('avg_uploaded_bytes'),
            fn.AVG(Job.subreddits_count).alias('avg_subreddits_count'),
            fn.AVG(Job.posted_messages).alias('avg_posted_messages')
        )
        .where(Job.start > delta)
        .group_by(Job.name)
        .order_by(fn.AVG(Job.duration).desc())
    )

    if not query:
        return

    return list(query)
