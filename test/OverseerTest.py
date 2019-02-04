import unittest
from unittest.mock import Mock

import psycopg2
from psycopg2 import ProgrammingError

from src.Overseer import *
from test.MessageMock import MessageMock
from test.SlaveMock import SlaveMock


class OverseerTest(unittest.TestCase):

    def setUp(self):
        # instantiate logger with test argument
        LoggingServer.getInstance(test=True)

        self._broadcaster = Mock()
        self._update_server = Mock()
        self._update_server.get_latest_state = Mock(return_value="TEST STATE")
        self._broadcaster.get_lock = Mock(return_value=Lock())
        self._broadcaster.get_update_server = Mock(return_value=self._update_server)

        self._db_operator = DBOperator("overseer_test", "inlatexbot", "inlatexbot", drop_key="r4jYi1@")

        self._sut = Overseer(self._broadcaster, self._db_operator)
        self._rm = ResourceManager()

    def testOnStart(self):
        update = Mock()

        message = MessageMock(text="/start")
        update.message = message

        self._sut.on_start(None, update)

        update.message.reply_text.assert_called_with(self._rm.get_string("greeting"))

    def testOnSubscribeWithNoSlaveName(self):
        update = Mock()
        update.message = MessageMock(text="/subscribe")

        self._sut.on_subscribe(None, update)
        update.message.reply_text.assert_called_with(self._rm.get_string("no_slave_nickname"))

    def testOnSubscribe(self):
        telegram_id = 123456

        reply_message = MessageMock(message_id=11)

        message = MessageMock(telegram_id,
                              text="/subscribe slave1",
                              reply_text=Mock(return_value=reply_message))

        update = Mock()
        update.message = message

        self._sut.on_subscribe(None, update)

        reply_message.message_id = 12
        update.message.text = "/subscribe slave2"

        self._sut.on_subscribe(None, update)

        self.assertIn(("slave1", 11), self._db_operator.get_subscriptions(telegram_id))
        self.assertIn(("slave2", 12), self._db_operator.get_subscriptions(telegram_id))

    def testOnUnsubscribe(self):
        telegram_id = 123456

        self._db_operator.add_user(UserMock(telegram_id))
        self._db_operator.add_slave(SlaveMock())
        self._db_operator.subscribe(telegram_id, "slave1", 11)

        message = MessageMock(telegram_id,
                              text="/unsubscribe slave1")
        update = Mock()
        update.message = message

        self._sut.on_unsubscribe(None, update)

        self.assertNotIn(("slave1", 11),
                         self._db_operator.get_subscriptions(telegram_id))
        update.message.reply_text.assert_called_with(self._rm.get_string("unsubscribed") % "slave1")

    def testOnCheckout(self):
        telegram_id = 123456

        update = Mock()
        update.message = MessageMock(telegram_id, text="/checkout slave1")

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="OK")]])

        self._sut.on_checkout(None, update)

        self._update_server.get_latest_state.assert_called_with("slave1")
        update.message.reply_text.assert_called_with("TEST STATE",
                                                     parse_mode="Markdown",
                                                     reply_markup=reply_markup)
