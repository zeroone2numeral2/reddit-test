from telegram import ParseMode

from .base_submission import BaseSenderType


class TextHandler(BaseSenderType):
    @staticmethod
    def test(submission):
        raise NotImplementedError

    def _entry_point(self, caption, reply_markup=None):
        return self._bot.send_message(
            self.chat_id,
            caption,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.style.webpage_preview or self._submission.force_disable_link_preview,
            reply_markup=reply_markup
        )
