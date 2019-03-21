from reddit.downloaders import VReddit


def main():
    v = VReddit('https://v.redd.it/goqe8yvmrfn21/DASH_1080?source=fallback')
    print(v)

    v.download()
    v.remove()


if __name__ == '__main__':
    main()
