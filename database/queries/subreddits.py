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
