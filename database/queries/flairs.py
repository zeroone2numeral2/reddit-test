import peewee

from ..models import Flair
from utilities import u


def save_flair(subreddit, flair):
    flair_lower = flair.lower()
    subreddit_name_lower = subreddit.lower()

    created = False
    try:
        flair = Flair.get(Flair.subreddit_name == subreddit_name_lower, Flair.flair == flair_lower)
        flair.last_seen_utc = u.now(utc=True)  # update last seen datetime
    except peewee.DoesNotExist:
        flair = Flair(subreddit_name=subreddit_name_lower, flair=flair_lower)
        created = True

    flair.save()

    return created


def get_flairs(subreddit_name):
    subreddit_name = subreddit_name.lower()

    query = (
        Flair.select(Flair.flair)
        .where(Flair.subreddit_name == subreddit_name)
    )

    if not query:
        return []

    return u.remove_duplicates([r.flair for r in query])
