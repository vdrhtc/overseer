import datetime
import time
from random import shuffle, randint
import unittest
from unittest.mock import Mock, call, MagicMock

from telegram import ParseMode

from src.Broadcaster import Broadcaster
from src.DBOperator import DBOperator
from src.LoggingServer import LoggingServer
from test.SlaveMock import SlaveMock
from test.UserMock import UserMock


class BroadcasterTest(unittest.TestCase):

    def setUp(self):
        LoggingServer.getInstance(test=True)

        self._telegram_updater = Mock()

        self._update_server = Mock()
        self._update_server.get_latest_state = Mock(return_value="TEST STATE")

        self._db_operator = DBOperator("overseer_test", "inlatexbot", "inlatexbot", drop_key="r4jYi1@")

        self._users = []
        full_names = ["Alex Korenkov", None, "Joe Marti", "Rob Shel", "Jens Koch",
                      "Sam Bad", "Chad Riget", "Will Oliver", "John Fowler", "Lena Egor"]
        for i in range(10):
            if full_names[i] is not None:
                name, surname = full_names[i].split(" ")
                nickname = "@%s%s" % (name[0], surname)
            else:
                nickname = None

            user = UserMock(12345 + i, full_name=full_names[i], nickname=nickname)
            self._users.append(user)
            self._db_operator.add_user(user)

        self._slaves = []
        for i in range(10):
            slave = SlaveMock("slave%d" % i, "0.0.0.%d" % i)
            self._slaves.append(slave)
            self._db_operator.add_slave(slave)

        # random cross-subscribe
        for user in self._users:
            slaves_copy = self._slaves.copy()
            shuffle(slaves_copy)
            slaves_monitored = slaves_copy[:randint(0, 9)]

            for slave in slaves_monitored:
                self._db_operator.subscribe(user.id, slave.nickname, randint(0, 100))

        self._sut = Broadcaster(self._telegram_updater, self._update_server,
                                        self._db_operator)

    def testBroadcastUpdates(self):

        def wait(*args, **kwargs):
            time.sleep(.1)

        self._telegram_updater.bot.edit_message_text = Mock(side_effect = wait)

        self._sut._broadcast_updates()

        for user in self._users:
            subs = self._db_operator.get_subscriptions(user.id)
            for sub in subs:
                args = "TEST STATE", user.id, sub[1]
                self._update_server.get_latest_state.assert_has_calls([call(sub[0])])
                self._telegram_updater.bot. \
                    edit_message_text.assert_has_calls([call(*args, parse_mode=ParseMode.MARKDOWN)])
