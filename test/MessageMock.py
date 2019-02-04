from datetime import datetime
from unittest.mock import Mock

from test.UserMock import UserMock


class MessageMock:

    def __init__(self, user_telegram_id=123456, message_id=1, user_full_name="Korenkov Alex",
                 user_telegram_nick="@lox", date=datetime.now(), text="I am a lox",
                 reply_text = Mock()):

        self.from_user = UserMock(user_telegram_id, user_full_name, user_telegram_nick)
        self.chat_id = user_telegram_id
        self.message_id = message_id
        self.date = date
        self.text = text
        self.reply_text = reply_text
