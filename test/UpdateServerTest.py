import unittest
from unittest.mock import MagicMock
from ssl import SSLError

from src.UpdateServer import *


class UpdateServerTest(unittest.TestCase):

    def setUp(self):

        self._tls_context = MagicMock()
        self._sut = UpdateServer(self._tls_context)
        self._sut._secure_socket = MagicMock()
        self._sut._secure_socket.accept = MagicMock(return_value = (MagicMock(), )*2)

    def testAcceptConnection(self):

        self._tls_context.wrap_socket = MagicMock()
        self._tls_context.wrap_socket.side_effect = SSLError()
        self._sut._accept_connection()

        self.assertEqual(self._sut._state, ServerState.ACCEPT)

        self._tls_context.wrap_socket = MagicMock()
        self._sut._accept_connection()

        self.assertEqual(self._sut._state, ServerState.DISPATCH)


