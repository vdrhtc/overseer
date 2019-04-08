import datetime
import itertools
import time
from random import shuffle, randint
import unittest
from unittest.mock import Mock, call, MagicMock

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton

from src.Broadcaster import Broadcaster
from src.DBOperator import DBOperator
from loggingserver import LoggingServer

from src.SlaveState import SlaveState
from test.SlaveMock import SlaveMock
from test.UserMock import UserMock


class BroadcasterTest(unittest.TestCase):

    def setUp(self):
        LoggingServer.getInstance("broadcaster", test=True)

        self._telegram_updater = Mock()

        self._update_server = Mock()
        self._mock_slave_state = SlaveState("slave1", "TEST STATE")
        self._mock_slave_state = SlaveState("slave2", "TEST STATE")

        self._db_operator = DBOperator("overseer_test", "inlatexbot", "inlatexbot",
                                       drop_key="r4jYi1@")

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
        self._slave_states = {}
        self._slave_state_raw_messages = ["TEST", "2018-01-01 00:00:00\r\ntest\r\nALERT!"]
        state_cycle = itertools.cycle(self._slave_state_raw_messages)
        for i in range(10):
            slave = SlaveMock("slave%d" % i, "0.0.0.%d" % i)
            self._slaves.append(slave)
            self._db_operator.add_slave(slave)
            self._slave_states[slave.nickname] = SlaveState(slave.nickname, next(state_cycle))

        self._update_server.get_latest_state = MagicMock(side_effect=
                                                         lambda x: self._slave_states[x])

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

        self._telegram_updater.bot.edit_message_text = Mock(side_effect=wait)

        self._sut._broadcast_updates()

        for user in self._users:
            subs = self._db_operator.get_subscriptions(user.id)
            for sub in subs:
                state = self._slave_states[sub[0]]

                args = state.get_state_message(), user.id, sub[1]
                self._update_server.get_latest_state.assert_has_calls([call(sub[0])])
                self._telegram_updater.bot. \
                    edit_message_text.assert_has_calls([call(*args,
                                                             parse_mode=ParseMode.MARKDOWN)])

                args = user.id, state.get_alert_message()
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("OK",
                                                                           callback_data="OK")]])

                if state.get_alert() != "":

                    self._telegram_updater.bot. \
                        send_message.assert_has_calls([call(*args,
                                                            parse_mode=ParseMode.MARKDOWN,
                                                            reply_markup=reply_markup)])
                else:
                    unexpected_call = call(*args,
                                           parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=reply_markup)
                    calls = self._telegram_updater.bot.send_message.mock_calls

                    self.assertNotIn(unexpected_call, calls)
