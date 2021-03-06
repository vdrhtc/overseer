import unittest
from unittest.mock import Mock, MagicMock
import psycopg2
from psycopg2._psycopg import ProgrammingError
from hashlib import md5


from src.DBOperator import DBOperator
from src.ResourceManager import ResourceManager
from test.MessageMock import MessageMock
from test.SlaveMock import SlaveMock
from test.UserMock import UserMock


class DBOperatorTest(unittest.TestCase):

    def setUp(self):

        self._conn = psycopg2.connect("dbname=%s user=%s password=%s"
                                      % ("overseer_test", "inlatexbot", "inlatexbot"))

        self._sut = DBOperator("overseer_test", "inlatexbot", "inlatexbot", drop_key="r4jYi1@")

        self._rm = ResourceManager()


    def testDbIndependentConnections(self):

        db_operator = DBOperator("overseer_test", "inlatexbot", "inlatexbot")
        # db_operator = self._sut
        try:
            db_operator._c.execute("INVALID_TRANSACTION")
        except ProgrammingError:
            pass

        user = UserMock()
        self._sut.add_user(user)
        users = self._sut.get_users()
        self.assertIn((user.id, user.full_name, user.name), users)

    def testAddUser(self):
        user = UserMock()
        self._sut.add_user(user)

        users = self._sut.get_users()

        self.assertIn((user.id, user.full_name, user.name), users)

        user1 = UserMock(135)

        # testing update
        with self._conn:
            c = self._conn.cursor()
            c.execute("INSERT INTO users (telegram_id) VALUES (%s)", [user1.id])

        self._sut.add_user(user1)

        users = self._sut.get_users()
        self.assertIn((user1.id, user1.full_name, user1.name), users)

    def testAddUserTwoTimes(self):

        user = UserMock()

        self._sut.add_user(user)
        self._sut.add_user(user)

        users = self._sut.get_users()

        self.assertEqual(len(users), 1)
        self.assertIn((user.id, user.full_name, user.name), users)

    def testAddSlave(self):

        slave1 = SlaveMock()
        slave2 = SlaveMock("slave2", password="test2pass", owner=45678)

        self._sut.add_slave(slave1)
        self._sut.add_slave(slave2)

        slaves = self._sut.get_slaves()

        slave1.password = md5(slave1.password.encode()).hexdigest()
        slave2.password = md5(slave2.password.encode()).hexdigest()

        self.assertListEqual([slave1.to_tuple(), slave2.to_tuple()], slaves)

        slave3 = SlaveMock("a"*60)  # long name

        try:
            self._sut.add_slave(slave3)
        except ValueError as e:
            self.assertEqual(e.args[0], self._rm.get_string("slave_name_too_long"))
        else:
            assert False

    def testAddSlaveTwoTimes(self):

        slave = SlaveMock()

        self._sut.add_slave(slave)

        try:
            self._sut.add_slave(slave)
        except ValueError as e:
            self.assertEqual(e.args[0], "Slave already exists")  # TODO:replace with rm
        else:
            assert False

        slaves = self._sut.get_slaves()

        slave.password = md5(slave.password.encode()).hexdigest()

        self.assertListEqual([slave.to_tuple()], slaves)

    def testUpdateSlave(self):

        slave = SlaveMock()

        self._sut.add_slave(slave)

        slave.password = "11ge!"

        self._sut.update_slave(slave)

        slaves = self._sut.get_slaves()

        slave.password = md5(slave.password.encode()).hexdigest()

        self.assertListEqual([slave.to_tuple()], slaves)



    def testGetSlave(self):

        slave = SlaveMock()

        self._sut.add_slave(slave)

        slave_from_db = self._sut.get_slave(slave.nickname)

        slave.password = md5(slave.password.encode()).hexdigest()

        self.assertEqual(slave.to_tuple(), slave_from_db)

        try:
            self._sut.get_slave("missing_slave")
        except ValueError:
            return
        else:
            assert False

    def testSubscribe(self):

        telegram_id = 123459
        self._sut.add_user(UserMock(telegram_id=telegram_id))
        self._sut.add_slave(SlaveMock())
        self._sut.add_slave(SlaveMock("slave2"))

        self._sut.subscribe(telegram_id, "slave1", 11)
        self._sut.subscribe(telegram_id, "slave2", 12)

        subs = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(subs, [("slave1", 11), ("slave2", 12)])

    def testIncorrectSubscribe(self):

        telegram_id = 123459
        user = UserMock(telegram_id=telegram_id)
        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0], "User %d not found" % telegram_id)

        self._sut.add_user(user)

        try:
            self._sut.subscribe(telegram_id, "slave1", 11)
        except ValueError as e:
            self.assertEqual(e.args[0], "Slave %s not found" % "slave1")

    def testDoubleSubscribe(self):
        # double subscribe
        telegram_id = 123459

        self._sut.add_user(UserMock(telegram_id=telegram_id))
        self._sut.add_slave(SlaveMock())

        self._sut.subscribe(telegram_id, "slave1", 11)

        subs = self._sut.get_subscriptions(telegram_id)
        self.assertListEqual(subs, [("slave1", 11)])

        self._sut.subscribe(telegram_id, "slave1", 12)
        subs = self._sut.get_subscriptions(telegram_id)
        self.assertListEqual(subs, [("slave1", 12)])

    def testUnsubscribe(self):

        telegram_id = 123459
        user = UserMock(telegram_id=telegram_id)

        self._sut.add_user(user)
        self._sut.add_slave(SlaveMock())
        self._sut.add_slave(SlaveMock("slave2"))

        self._sut.subscribe(telegram_id, "slave1", 11)
        self._sut.subscribe(telegram_id, "slave2", 12)

        subs = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(subs, [("slave1", 11), ("slave2", 12)])

        self._sut.unsubscribe(telegram_id, "slave1")
        self._sut.unsubscribe(telegram_id, "slave2")

        subs = self._sut.get_subscriptions(telegram_id)

        self.assertListEqual(subs, [])

        with self.assertRaises(ValueError):
            self._sut.unsubscribe(telegram_id, "slave2123123")  # no such slave

        with self.assertRaises(ValueError):
            self._sut.unsubscribe(11, "slave2")  # no such user

    def testGetSubscribers(self):
        user1 = UserMock()
        user2 = UserMock(123460, full_name="Joe Marti", nickname="@pidr")
        slave1 = SlaveMock()
        slave2 = SlaveMock("slave2")

        self._sut.add_user(user1)
        self._sut.add_user(user2)
        self._sut.add_slave(slave1)
        self._sut.add_slave(slave2)

        def info_message_ids():
            for i in range(4):
                yield i + 1

        gen = info_message_ids()
        for user in self._sut.get_users():
            for slave in self._sut.get_slaves():
                uid, snick, m = user.telegram_id, slave.slave_nickname, next(gen)
                self._sut.subscribe(uid, snick, m)

        self.assertListEqual(self._sut.get_subscriptions(user1.id), [(slave1.nickname, 1), (slave2.nickname, 2)])
        self.assertListEqual(self._sut.get_subscriptions(user2.id), [(slave1.nickname, 3), (slave2.nickname, 4)])

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
        self.assertEqual(message_repr[5], md5("I am a lox".encode()).hexdigest())
