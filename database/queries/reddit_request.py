import datetime

from peewee import fn

from ..models import RedditRequest


def delete_old(days=14):
    query = RedditRequest.delete().where(RedditRequest.request_datetime_utc < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
    return query.execute()  # returns the number of deleted rows


def save_request(subreddit, account_name, client_name, dt=None):
    if not dt:
        dt = datetime.datetime.utcnow()

    reddit_request = RedditRequest(
        subreddit=subreddit,
        subreddit_name=subreddit.name,
        account_name=account_name,
        client_name=client_name,
        request_datetime_utc=dt
    )
    reddit_request.save()


def least_stressed(creds_type, valid_names, days=2):
    delta = datetime.datetime.utcnow() - datetime.timedelta(days=days)
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

    if not query:
        return

    # if valid_names contains a name that we haven't used yet (not in the db), use that one
    db_items = [item.name for item in query]
    unused_config_items = list(set(valid_names) - set(db_items))
    if unused_config_items:
        return unused_config_items[0]

    return query[0].name


def creds_usage(valid_accouns=None, valid_clients=None, days=2):
    delta = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = (
        RedditRequest.select(RedditRequest.account_name, RedditRequest.client_name, fn.Count(RedditRequest.id).alias('count'))
        .where(
            RedditRequest.request_datetime_utc > delta,
            RedditRequest.account_name << valid_accouns if valid_accouns else True,
            RedditRequest.client_name << valid_clients if valid_clients else True
        )
        .group_by(RedditRequest.account_name, RedditRequest.client_name)
        .order_by(fn.Count(RedditRequest.id).desc())  # ascending by default
    ).dicts()

    return [row for row in query]
