import peewee

from ..models import Subreddit
from ..models import Channel


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


def avg_value(column_name):
    if column_name == 'max_frequency':
        column = Subreddit.max_frequency
    elif column_name == 'limit':
        column = Subreddit.limit
    elif column_name == 'number_of_posts':
        column = Subreddit.number_of_posts
    else:
        raise ValueError('pass a valid column name')

    query = Subreddit.select(column.alias('name')).where(Subreddit.enabled == True)
    items = [s.name for s in query]

    average = sum(items) / len(items)
    return int(average)
