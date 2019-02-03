import unittest
from unittest.mock import Mock, MagicMock
from time import sleep
import psycopg2

from src.DBOperator import *
from test.MessageMock import MessageMock


class DBOperatorTest(unittest.TestCase):

    def setUp(self):

        self._conn = psycopg2.connect("dbname=%s user=%s password=%s"
                                      % ("overseer_test", "inlatexbot", "inlatexbot"))

        self._sut = DBOperator("overseer_test", "inlatexbot", "inlatexbot", drop_key="r4jYi1@")

    def testAddUser(self):

        telegram_id = 123459

        self._sut.add_user(telegram_id)

        telegram_ids = self._sut.get_users()

        self.assertTrue(123459 in telegram_ids)

    def testAddUserTwoTimes(self):

        telegram_id = 123459

        self._sut.add_user(telegram_id)
        self._sut.add_user(telegram_id)

        telegram_ids = self._sut.get_users()

        self.assertEqual(len(telegram_ids), 1)
        self.assertTrue(telegram_id in telegram_ids)

    def testAddSlave(self):

        slave_nickname = "slave1"

        self._sut.add_slave(slave_nickname, "0.0.0.0")

        slave_nicknames = self._sut.get_slaves()

        self.assertTrue(slave_nickname in slave_nicknames)

    def testAddSlaveTwoTimes(self):

        slave_nickname = "slave1"

        self._sut.add_slave(slave_nickname, "0.0.0.0")
        self._sut.add_slave(slave_nickname, "0.0.0.0")

        slave_nicknames = self._sut.get_slaves()

        self.assertEqual(len(slave_nicknames), 1)
        self.assertTrue(slave_nickname in slave_nicknames)

    def testSubscribe(self):

        telegram_id = 123459
        self._sut.add_user(telegram_id)
        self._sut.add_slave("slave1", "0.0.0.0")
        self._sut.add_slave("slave2", "0.0.0.0")

        self._sut.subscribe(telegram_id, "slave1", 11)
        self._sut.subscribe(telegram_id, "slave2", 12)

        slaves = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(slaves, [("slave1", 11), ("slave2", 12)])

    def testIncorrectSubscribe(self):

        telegram_id = 123459
        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0], "User %d not found" % telegram_id)

        self._sut.add_user(telegram_id)

        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0], "Slave %s not found" % "slave1")

    def testDoubleSubscribe(self):
        # double subscribe
        telegram_id = 123459

        self._sut.add_user(telegram_id)
        self._sut.add_slave("slave1", "0.0.0.0")
        self._sut.subscribe(telegram_id, "slave1", 11)

        slaves = self._sut.get_subscriptions(telegram_id)
        self.assertListEqual(slaves, [("slave1", 11)])

        self._sut.subscribe(telegram_id, "slave1", 12)
        slaves = self._sut.get_subscriptions(telegram_id)
        self.assertListEqual(slaves, [("slave1", 12)])

    def testUnsubscribe(self):

        telegram_id = 123459
        self._sut.add_user(telegram_id)
        self._sut.add_slave("slave1", "0.0.0.0")
        self._sut.add_slave("slave2", "0.0.0.0")

        self._sut.subscribe(telegram_id, "slave1", 11)
        self._sut.subscribe(telegram_id, "slave2", 12)

        slaves = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(slaves, [("slave1", 11), ("slave2", 12)])

        self._sut.unsubscribe(telegram_id, "slave1")
        self._sut.unsubscribe(telegram_id, "slave2")

        slaves = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(slaves, [])

        with self.assertRaises(ValueError):
            self._sut.unsubscribe(telegram_id, "slave2123123")  # no such slave

        with self.assertRaises(ValueError):
            self._sut.unsubscribe(11, "slave2")  # no such user

    def testGetSubscribers(self):

        self._sut.add_user(123459)
        self._sut.add_user(123460)
        self._sut.add_slave("slave1", "0.0.0.0")
        self._sut.add_slave("slave2", "0.0.0.0")

        def info_message_ids():
            for i in range(4):
                yield i + 1

        gen = info_message_ids()
        for user in self._sut.get_users():
            for slave_nickname in self._sut.get_slaves():
                u, s, m = user, slave_nickname, next(gen)
                # print(u,s,m)
                self._sut.subscribe(u, s, m)

        # self.assertTrue(False)
        #
        #
        self.assertListEqual(self._sut.get_subscriptions(123459), [("slave1", 1), ("slave2", 2)])
        self.assertListEqual(self._sut.get_subscriptions(123460), [("slave1", 3), ("slave2", 4)])

    def testAddMessage(self):

        telegram_id = 123456
        message = MessageMock(telegram_id)

        self._sut.add_message(message)

        messages = self._sut.get_messages(telegram_id)
        self.assertEqual(len(messages), 1)
        message_repr = messages[0]
        self.assertEqual(message_repr[0], telegram_id)
        self.assertEqual(message_repr[1], 1)
        self.assertEqual(message_repr[2], "Korenkov Alex")
        self.assertEqual(message_repr[3], "@lox")
        self.assertEqual(message_repr[4], message.date)
        self.assertEqual(message_repr[5], "I am a lox")
