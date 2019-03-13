from reddit import reddit
from reddit import Sender


class subreddit:
    sorting = 'hot'


def main():
    print('getting one submission...')
    for submission in reddit.subreddit('all').hot(limit=1):
        sender = Sender(None, None, subreddit, submission)

        with open('template_keys.txt', 'w+') as f:
            print('writing file...')
            f.write('\n'.join(sender.template_keys))


if __name__ == '__main__':
    main()
