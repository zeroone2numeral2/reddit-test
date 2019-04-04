from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove


class Keyboard:
    REMOVE = ReplyKeyboardRemove()

    @staticmethod
    def from_list(buttons, resize_keyboard=True):
        markup = []
        for button in buttons:
            markup.append([button])

        return ReplyKeyboardMarkup(markup, resize_keyboard=resize_keyboard)
