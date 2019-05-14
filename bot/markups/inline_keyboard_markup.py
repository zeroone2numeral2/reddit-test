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
