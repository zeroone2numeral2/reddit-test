from utilities import u


def main():
    class s:
        enabled = True
        enabled_resume = False

        quiet_hours_start = 22
        quiet_hours_end = 6
        quiet_hours_demultiplier = 0.0

        number_of_posts = 1

        max_frequency = 115

    u.number_of_daily_posts(s, print_debug=True)


if __name__ == '__main__':
    main()
