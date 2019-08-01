import unittest
from unittest.mock import Mock
from hashlib import md5

from src.Overseer import *
from test.MessageMock import MessageMock
from test.SlaveMock import SlaveMock
from test.UserMock import UserMock


class OverseerTest(unittest.TestCase):

    def setUp(self):
        # instantiate logger with test argument
        LoggingServer.getInstance("overseer", test=True)

        self._broadcaster = Mock()
        self._update_server = Mock()
        self._update_server.get_latest_state = Mock(return_value="TEST STATE")
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

        slave1 = SlaveMock()
        slave2 = SlaveMock("slave2", password="test2pass", owner=45678)

        self._db_operator.add_slave(slave1)
        self._db_operator.add_slave(slave2)

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


        reply_message.message_id = 13
        update.message.text = "/subscribe slave3"
        message.reply_text = Mock()

        try:
            self._sut.on_subscribe(None, update)
        except ValueError as e:
            self.assertEqual(e.args[0], "Slave slave3 not found")
            message.reply_text.assert_called_with(self._rm.get_string("no_slave"))

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


    def testSlaveRegistration(self):

        telegram_id1 = 123456
        telegram_id2 = 1234567
        telegram_id3 = 12345678

        update = Mock()
        update.message = MessageMock(telegram_id1, text="/register")
        update2 = Mock()
        update2.message = MessageMock(telegram_id2, text="/register")

        self._sut.on_register_slave(None, update)
        self._sut.on_register_slave(None, update2)

        update3 = Mock()
        update3.message = MessageMock(telegram_id3, text="/register")

        self._sut.on_register_slave(None, update3)


        update.message = MessageMock(telegram_id1, text="slave1")
        update2.message = MessageMock(telegram_id2, text="slave2")

        self._sut.on_message(None, update)
        self._sut.on_message(None, update2)


        update.message = MessageMock(telegram_id1, text="passw1ord")
        update2.message = MessageMock(telegram_id2, text="passw1ord2")
        update3.message = MessageMock(telegram_id3, text="slave3")

        self._sut.on_message(None, update)
        self._sut.on_message(None, update2)
        self._sut.on_message(None, update3)

        update3.message = MessageMock(telegram_id3, text="passw1ord3")
        self._sut.on_message(None, update3)


        self.assertIn(("slave1", "0.0.0.0", telegram_id1, md5("passw1ord".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        self.assertIn(("slave2", "0.0.0.0", telegram_id2, md5("passw1ord2".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        self.assertIn(("slave3", "0.0.0.0", telegram_id3, md5("passw1ord3".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        for tid in [telegram_id1, telegram_id2, telegram_id3]:
            self.assertNotIn(tid, self._sut._slave_registration_conversations.keys())
            self.assertNotIn(tid, self._sut._slave_registration_data.keys())

    def testSlaveRegistrationAbort(self):

        telegram_id1 = 123456
        telegram_id2 = 1234567
        telegram_id3 = 12345678

        update = Mock()
        update.message = MessageMock(telegram_id1, text="/register")
        update2 = Mock()
        update2.message = MessageMock(telegram_id2, text="/register")

        self._sut.on_register_slave(None, update)
        self._sut.on_register_slave(None, update2)

        update3 = Mock()
        update3.message = MessageMock(telegram_id3, text="/register")

        self._sut.on_register_slave(None, update3)


        update.message = MessageMock(telegram_id1, text="/abort")
        update2.message = MessageMock(telegram_id2, text="slave2")

        self._sut.on_abort(None, update)
        self._sut.on_message(None, update2)

        update2.message = MessageMock(telegram_id2, text="/abort")
        update3.message = MessageMock(telegram_id3, text="slave3")

        self._sut.on_abort(None, update2)
        self._sut.on_message(None, update3)

        update3.message = MessageMock(telegram_id3, text="passw1ord3")
        self._sut.on_message(None, update3)


        self.assertNotIn(("slave1", "0.0.0.0", telegram_id1, md5("passw1ord".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        self.assertNotIn(("slave2", "0.0.0.0", telegram_id2, md5("passw1ord2".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        self.assertIn(("slave3", "0.0.0.0", telegram_id3, md5("passw1ord3".encode()).hexdigest()),
                      self._db_operator.get_slaves())

        for tid in [telegram_id1, telegram_id2, telegram_id3]:
            self.assertNotIn(tid, self._sut._slave_registration_conversations.keys())
            self.assertNotIn(tid, self._sut._slave_registration_data.keys())

