from pprint import pprint

from reddit import reddit
from utilities import u


def main():
    for submission in reddit.subreddit('ricardo_test').new(limit=1):
        """
        if submission.crosspost_parent:
            print('Getting parent submission:', submission.crosspost_parent)
            submission = reddit.submission(submission.crosspost_parent)
        """

        u.print_submission(submission)
        pprint(submission.crosspost_parent_list[0]['media'])


if __name__ == '__main__':
    main()
