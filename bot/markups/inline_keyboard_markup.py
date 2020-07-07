from telegram import InlineKeyboardMarkup
from telegram import InlineKeyboardButton


class InlineKeyboard:
    REMOVE = None

    @staticmethod
    def row_from_list(buttons_list):
        keyboard = []
        for button in buttons_list:
            keyboard.append([InlineKeyboardButton(button[0], callback_data=button[1])])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def vote(submission_id, voted_for=''):
        keyboard = [[
            InlineKeyboardButton('{} ⬆'.format('' if not voted_for == 'upvote' else '✅'), callback_data='upvote:{}'.format(submission_id)),
            InlineKeyboardButton('{} ⬇'.format('' if not voted_for == 'downvote' else '✅'), callback_data='downvote:{}'.format(submission_id))
        ]]

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def post_buttons(url=None, comments=None, n_comments=None):
        if url and comments and url.lower() == comments.lower():
            keyboard = [[InlineKeyboardButton('thread • {}'.format(n_comments), url=comments)]]
        else:
            keyboard = [[]]
            if url:
                keyboard[0].append(InlineKeyboardButton('url', url=url))
            if comments:
                button_text = 'comments'
                if n_comments:
                    button_text += ' • ' + str(n_comments)

                keyboard[0].append(InlineKeyboardButton(button_text, url=comments))

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def post_buttons_with_labels(
            url_button_url=None,
            url_button_label=None,
            comments_button_url=None,
            comments_button_label=None
    ):
        if url_button_label is None:
            url_button_label = 'url'
        if comments_button_label is None:
            comments_button_label = 'comments'

        if url_button_url and comments_button_url and url_button_url.lower() == comments_button_url.lower():
            keyboard = [[InlineKeyboardButton(comments_button_label, url=comments_button_url)]]
            return InlineKeyboardMarkup(keyboard)

        keyboard = [[]]
        if url_button_url is not None:
            keyboard[0].append(InlineKeyboardButton(url_button_label, url=url_button_url))
        if comments_button_url is not None:
            keyboard[0].append(InlineKeyboardButton(comments_button_label, url=comments_button_url))

        return InlineKeyboardMarkup(keyboard)
