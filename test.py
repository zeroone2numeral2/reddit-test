from math import floor


def main():
    def number_of_daily_posts(s):
        n = 0
        if s.enabled:
            hours_of_reduced_frequency = 0
            if s.quiet_hours_demultiplier != 1.0:
                if s.quiet_hours_start > s.quiet_hours_end:
                    hours_of_reduced_frequency += 24 - s.quiet_hours_start
                    hours_of_reduced_frequency += s.quiet_hours_end + 1
                elif s.quiet_hours_start < s.quiet_hours_end:
                    hours_of_reduced_frequency += s.quiet_hours_end - s.quiet_hours_start + 1

            hours_of_normal_frequency = 24 - hours_of_reduced_frequency

            minutes_of_normal_frequencies = hours_of_normal_frequency * 60
            minutes_of_reduced_frequency = hours_of_reduced_frequency * 60

            # number of messages during normal hours
            n_during_normal_hours = (minutes_of_normal_frequencies / s.max_frequency) * s.number_of_posts

            n_during_quiet_hours = 0
            if minutes_of_reduced_frequency:
                # number of messages during quiet hours
                n_during_quiet_hours = (minutes_of_reduced_frequency / (s.max_frequency * s.quiet_hours_demultiplier)) * s.number_of_posts

            n += n_during_normal_hours + n_during_quiet_hours

            n = int(n)

        if s.enabled_resume:
            n += s.number_of_posts


        print('normal freq.: {}\nreduced freq.: {}\nq.h. start: {}\nq.h. end: {}\nnormal h. messages: {}\nq.h. messages: {}'.format(
            hours_of_normal_frequency,
            hours_of_reduced_frequency,
            s.quiet_hours_start,
            s.quiet_hours_end,
            n_during_normal_hours,
            n_during_quiet_hours
        ))

        return n


    class s:
        enabled = True
        enabled_resume = True

        quiet_hours_start = 4
        quiet_hours_end = 7
        quiet_hours_demultiplier = 1.5

        number_of_posts = 2

        max_frequency = 120

    print('n:', number_of_daily_posts(s))




if __name__ == '__main__':
    main()
