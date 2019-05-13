import argparse
import urllib.request

import praw

from config import config

parser = argparse.ArgumentParser()

reddit = praw.Reddit(
    client_id=config.praw.client_id,
    client_secret=config.praw.client_secret,
    user_agent=config.praw.user_agent
)


def main(sub_name):
    sub = reddit.subreddit(sub_name)
    print('url:', sub.icon_img)

    file_path = 'icon_{}.png'.format(sub_name)

    with urllib.request.urlopen(sub.icon_img) as response, open(file_path, 'wb') as out_file:
        data = response.read()
        out_file.write(data)

    print('icon saved to:', file_path)


if __name__ == '__main__':
    parser.add_argument(
        '-s',
        '--subreddit',
        type=str,
        help='subreddit name',
        required=True
    )

    args = parser.parse_args()

    main(args.subreddit)
