from reddit import reddit
from utilities import u


def main():
    for submission in reddit.subreddit('anime').new(limit=1):
        u.print_submission(submission)


if __name__ == '__main__':
    main()
