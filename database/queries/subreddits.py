import peewee
from peewee import fn
from peewee import Case

from ..models import Subreddit
from ..models import Channel
from utilities import u


def subreddits_invite_link() -> [Channel]:
    query = (
        Channel.select(
            Channel.channel_id,
            Channel.title,
            Channel.invite_link,
            peewee.fn.GROUP_CONCAT(Subreddit.name, ', ').coerce(False).alias('subreddits')
        )
        .join(Subreddit)
        .where((Subreddit.enabled == True) | (Subreddit.enabled_resume == True))
        .group_by(Channel.channel_id)
        .order_by(peewee.fn.lower(Channel.title))
        .dicts()
    )

    return [{**channel, 'subreddits': channel['subreddits'].split(', ')} for channel in query]


def enabled_count():
    return Subreddit.select().where(Subreddit.enabled == True).count()


def avg_value(column_name, round_by=0):
    if column_name == 'max_frequency':
        column = Subreddit.max_frequency
    elif column_name == 'number_of_posts':
        column = Subreddit.number_of_posts
    else:
        raise ValueError('pass a valid column name')

    query = Subreddit.select(column.alias('name')).where(Subreddit.enabled == True)
    items = [int(s.name) for s in query]

    average = sum(items) / len(items)
    print(average, u.proper_round(average))
    return u.proper_round(average, round_by)


def avg_limit():
    query = (
        Subreddit.select(
            Subreddit.limit,
            Case(None, [((Subreddit.limit == None), Subreddit.limit.default)], Subreddit.limit).alias('actual_limit')
        )
        .where(Subreddit.enabled == True)
    )
    items = [s.actual_limit for s in query]

    average = sum(items) / len(items)
    return int(average)


def avg_daily_fetched_submissions(round_by=2):
    query = Subreddit.select().where(Subreddit.enabled == True)
    items = [s.daily_fetched_submissions for s in query]

    average = sum(items) / len(items)
    return u.proper_round(average, round_by)
