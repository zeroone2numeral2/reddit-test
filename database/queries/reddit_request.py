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


def least_stressed_account(valid_names, days=2):
    delta = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = (
        RedditRequest.select(RedditRequest.account_name, fn.Count(RedditRequest.id).alias('count'))
        .where(RedditRequest.request_datetime_utc > delta and RedditRequest.account_name in valid_names)
        .group_by(RedditRequest.account_name)
        .order_by(fn.Count(RedditRequest.id))  # ascending by default
    )

    for account in query:
        print('', account.account_name, account.count)

    return query[0].account_name


def least_stressed_client(valid_names, days=2):
    delta = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    query = (
        RedditRequest.select(RedditRequest.client_name, fn.Count(RedditRequest.id).alias('count'))
        .where(RedditRequest.request_datetime_utc > delta and RedditRequest.client_name in valid_names)
        .group_by(RedditRequest.client_name)
        .order_by(fn.Count(RedditRequest.id))  # ascending by default
    )

    for client in query:
        print('', client.client_name, client.count)

    return query[0].client_name

