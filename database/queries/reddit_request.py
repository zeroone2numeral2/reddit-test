import datetime

from peewee import fn

from ..models import RedditRequest
from config import reddit


def delete_old(days=14):
    query = RedditRequest.delete().where(RedditRequest.request_datetime_utc < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
    return query.execute()  # returns the number of deleted rows


def save_request(subreddit, account_name, client_name, weight=1, dt=None):
    if not dt:
        dt = datetime.datetime.utcnow()

    reddit_request = RedditRequest(
        subreddit=subreddit,
        subreddit_name=subreddit.name,
        account_name=account_name,
        client_name=client_name,
        weight=weight,
        request_datetime_utc=dt
    )
    reddit_request.save()


def least_stressed(creds_type, valid_names, hours=None) -> list:
    """Will return a list of clients names
    If valid_names contains clients that have never been used as per the database, then these clients will be returned
    Else, it will return a list of clients from the least used to the most used one"""
    if not hours:
        hours = reddit.general.stress_threshold_hours

    delta = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    if creds_type == 'account':
        group_by = RedditRequest.account_name
    elif creds_type == 'client':
        group_by = RedditRequest.client_name
    else:
        raise ValueError

    query = (
        RedditRequest.select(group_by.alias('name'), fn.Count(RedditRequest.id).alias('count'))
        .where(RedditRequest.request_datetime_utc > delta, group_by << valid_names)
        .group_by(group_by)
        .order_by(fn.Count(RedditRequest.id))  # ascending by default
    )

    # if valid_names contains a name that we haven't used yet (not in the db), use that one
    # if there are no items in the db, the full list will be used
    db_items = [item.name for item in query]
    unused_config_items = list(set(valid_names) - set(db_items))
    if unused_config_items:
        return unused_config_items

    return [row.name for row in query]  # first element -> less usage


def creds_usage(valid_accouns=None, valid_clients=None, hours=None):
    if not hours:
        hours = reddit.general.stress_threshold_hours

    delta = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    query = (
        RedditRequest.select(RedditRequest.account_name, RedditRequest.client_name, fn.Count(RedditRequest.id).alias('count'))
        .where(
            RedditRequest.request_datetime_utc > delta,
            ((RedditRequest.account_name << valid_accouns if valid_accouns else True) | (RedditRequest.account_name.is_null())),
            RedditRequest.client_name << valid_clients if valid_clients else True
        )
        .group_by(RedditRequest.account_name, RedditRequest.client_name)
        .order_by(fn.Count(RedditRequest.id).desc())  # ascending by default
    ).dicts()

    return [row for row in query]
