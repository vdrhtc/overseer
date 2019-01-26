import unittest
from unittest.mock import Mock, MagicMock
from time import sleep
import psycopg2


from src.DBOperator import *

class DBOperatorTest(unittest.TestCase):

    def setUp(self):

        self._conn = psycopg2.connect("dbname=%s user=%s password=%s"
                                      % ("overseer_test", "inlatexbot", "inlatexbot"))

        self._c = self._conn.cursor()
        with self._conn:
            self._c.execute("DROP TABLE users, slaves, subscriptions;")

        self._sut = DBOperator("overseer_test", "inlatexbot", "inlatexbot")
        self._sut.create_tables()

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

        slave_nicknames = [slave[1] for slave in self._sut.get_slaves()]

        self.assertTrue(slave_nickname in slave_nicknames)

    def testAddSlaveTwoTimes(self):

        slave_nickname = "slave1"

        self._sut.add_slave(slave_nickname, "0.0.0.0")
        self._sut.add_slave(slave_nickname, "0.0.0.0")

        slave_nicknames = [slave[1] for slave in self._sut.get_slaves()]

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
            self.assertEqual(e.args[0], "User %d not found"%telegram_id)

        self._sut.add_user(telegram_id)

        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0], "Slave %s not found"%"slave1")

        # double subscribe
        self._sut.add_slave("slave1", "0.0.0.0")
        self._sut.subscribe(telegram_id, "slave1", 11)
        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0],
                             "User 123459 is already subscribed to slave slave1")

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