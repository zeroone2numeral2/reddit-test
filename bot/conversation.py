class Status:
    SUBREDDIT_SELECT = 10
    CHANNEL_SELECT = 20
    WAITING_ORIGIN_SUBREDDIT = 30
    WAITING_FORWARDED_MESSAGE = 40
    END = -1
    NONE_RETURNED = -10  # this is for handlers that are not parte of a conversation, so they ruturn None


STATUSES_DICT = {
    Status.END: 'conversation ended',
    Status.SUBREDDIT_SELECT: 'SUBREDDIT_SELECT',
    Status.CHANNEL_SELECT: 'CHANNEL_SELECT',
    Status.WAITING_ORIGIN_SUBREDDIT: 'WAITING_ORIGIN_SUBREDDIT',
    Status.WAITING_FORWARDED_MESSAGE: 'WAITING_FORWARDED_MESSAGE',
    Status.NONE_RETURNED: 'no next status returned'
}


def get_status_description(status_value):
    return STATUSES_DICT.get(status_value, 'unmapped value')
