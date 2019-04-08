import unittest
import datetime
from unittest.mock import patch, MagicMock

from src.SlaveState import SlaveState


class SlaveStateTest(unittest.TestCase):

    def setUp(self):

        self._received_at = datetime.datetime(2018, 1,1,0,0,0)
        self._now_mock = MagicMock(return_value = self._received_at)
        self._dt_mock = MagicMock()
        self._dt_mock.now = self._now_mock

        self._raw_msg_1 = "test"
        self._raw_msg_2 = "1996-01-01 00:00:00\r\ntest state\r\nSLAVE failing!"

        self._slave_nick = "slave1"

    def testGetStateMessage(self):


        with patch("datetime.datetime", new = self._dt_mock):
            self._sut = SlaveState(self._slave_nick, self._raw_msg_1)

        self.assertEqual(self._sut.get_state_message(), '2018-01-01 00:00:00 - slave1\n'
                                                        'test')

        with patch("datetime.datetime", new = self._dt_mock):
            self._sut = SlaveState(self._slave_nick, self._raw_msg_2)

        self.assertEqual(self._sut.get_state_message(), '2018-01-01 00:00:00 - slave1\n'
                                                        'test state')

    def testGetAlert(self):

        with patch("datetime.datetime", new = self._dt_mock):
            self._sut = SlaveState(self._slave_nick, self._raw_msg_2)

        self.assertEqual(self._sut.get_alert_message(), '2018-01-01 00:00:00 - slave1\n'
                                                'Alert! SLAVE failing!')

