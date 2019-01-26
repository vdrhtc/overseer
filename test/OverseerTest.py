import unittest
from unittest.mock import Mock

import psycopg2
from psycopg2 import ProgrammingError

from src.Overseer import *


class OverseerTest(unittest.TestCase):

    def setUp(self):

        broadcaster = Mock()
        broadcaster.get_lock = Mock(return_value=Lock())

        conn = psycopg2.connect("dbname=%s user=%s password=%s"
                                     % ("overseer_test", "inlatexbot", "inlatexbot"))

        c = conn.cursor()
        try:
            with conn:
                c.execute("DROP TABLE users, slaves, subscriptions;")
        except ProgrammingError:
            pass

        self._db_operator = DBOperator("overseer_test", "inlatexbot", "inlatexbot")
        self._db_operator.create_tables()

        self._sut = Overseer(broadcaster, self._db_operator)
        self._rm = ResourceManager()

    def testOnStart(self):

        update = Mock()

        self._sut.on_start(None, update)

        update.message.reply_text.assert_called_with(self._rm.get_string("greeting"))

    def testOnSubscribeWithNoSlaveName(self):

        update = Mock()
        update.message.text = "/subscribe"

        self._sut.on_subscribe(None, update)
        update.message.reply_text.assert_called_with(self._rm.get_string("no_slave_nickname"))

    def testOnSubscribe(self):

        telegram_id = 123456

        update = Mock()
        update.message.chat_id = telegram_id
        reply_message = Mock()
        reply_message.message_id = 11
        update.message.reply_text = Mock(return_value=reply_message)
        update.message.text = "/subscribe slave1"

        self._sut.on_subscribe(None, update)

        self.assertIn(("slave1", 11), self._db_operator.get_subscriptions(telegram_id))

    def testOnUnsubscribe(self):

        telegram_id = 123456

        self._db_operator.add_user(telegram_id)
        self._db_operator.add_slave("slave1", "0.0.0.0")
        self._db_operator.subscribe(telegram_id, "slave1", 11)

        update = Mock()
        update.message.chat_id = telegram_id
        reply_message = Mock()
        update.message.reply_text = Mock(return_value=reply_message)
        update.message.text = "/unsubscribe slave1"

        self._sut.on_unsubscribe(None, update)

        self.assertNotIn(("slave1", 11),
                         self._db_operator.get_subscriptions(telegram_id))
        update.message.reply_text.assert_called_with(self._rm.get_string("unsubscribed") % "slave1")
