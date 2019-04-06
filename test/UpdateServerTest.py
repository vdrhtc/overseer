import unittest
from unittest.mock import MagicMock
from ssl import SSLError

from src.UpdateServer import *
from test.SlaveMock import SlaveMock


class UpdateServerTest(unittest.TestCase):

    def setUp(self):
        LoggingServer.getInstance("overseer-update-server", test=True)

        self._tls_context = MagicMock()
        self._db_operator = MagicMock()
        self._sut = UpdateServer(self._tls_context, self._db_operator)
        self._sut._secure_socket = MagicMock()
        self._sut._secure_socket.accept = MagicMock(return_value=(MagicMock(),) * 2)

    def testAcceptConnection(self):
        self._tls_context.wrap_socket = MagicMock()
        self._tls_context.wrap_socket.side_effect = SSLError()
        self._sut._accept_connection()

        self.assertEqual(self._sut._state, ServerState.ACCEPT)

        self._tls_context.wrap_socket = MagicMock()
        self._sut._accept_connection()

        self.assertEqual(self._sut._state, ServerState.DISPATCH)

    def testAuthenticateSlave(self):

        auth = self._sut._authenticate_slave("test", "test_pass")

        self.assertFalse(auth)

        slave = SlaveMock()
        slave_from_db = SlaveMock(password=md5(slave.password.encode()).hexdigest())

        self._db_operator.get_slave = MagicMock(return_value=slave_from_db)

        auth = self._sut._authenticate_slave(slave.nickname, slave.password)

        self.assertTrue(auth)

        slave = SlaveMock(password="")
        slave_from_db = SlaveMock(password=md5(slave.password.encode()).hexdigest())

        auth = self._sut._authenticate_slave(slave.nickname, "")

        self.assertFalse(auth)


    def testCommunicate(self):
        conn = MagicMock()
        conn.recv = MagicMock(side_effect=["slave1\r\npass".encode()]+
                                           ["state".encode()]*10 +
                                           ["".encode()])

        slave = SlaveMock(password="pass")
        slave_from_db = SlaveMock(password=md5(slave.password.encode()).hexdigest())

        self._db_operator.get_slave = MagicMock(return_value=slave_from_db)

        self._sut._communicate(conn, MagicMock())

        self.assertEqual(self._sut._latest_states[slave.nickname], "state")


        conn.recv = MagicMock(side_effect=["slave2\r\npassss@".encode(),
                                           "state".encode(),
                                           "".encode()])

        self._sut._communicate(conn, MagicMock())
        self.assertNotIn("slave2", self._sut._latest_states.keys())
