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
