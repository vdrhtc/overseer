import socket
import ssl
from enum import Enum, auto

from threading import Thread, Lock

from src.LoggingServer import LoggingServer
from src.ResourceManager import ResourceManager


class ServerState(Enum):
    ACCEPT = auto()
    DISPATCH = auto()


class UpdateServer:

    def __init__(self, tls_context):

        self._rm = ResourceManager()
        self._host = "0.0.0.0"
        self._port = 5000  # initiate port no above 1024
        self._secure_port = 5000
        self._stop = False
        self._socket = None

        self._secure_socket = None
        self._tls_context = tls_context

        self._logger = LoggingServer.getInstance()

        self._latest_states = {}

        self._strategies = {ServerState.ACCEPT: self._accept_connection,
                            ServerState.DISPATCH: self._dispatch_connection}
        self._state = ServerState.ACCEPT

        self._connection_to_dispatch = None

    def launch(self):

        self._stop = False

        self._secure_socket = socket.socket()
        self._secure_socket.bind((self._host, self._secure_port))
        self._secure_socket.listen()
        self._logger.info("UpdateServer: secure listening on %s" % str((self._host, self._port)))

        connection_dispatcher = Thread(target=self._act)
        connection_dispatcher.setDaemon(True)
        connection_dispatcher.start()

    def stop(self):
        self._stop = True

    def _act(self):
        try:
            while not self._stop:
                self._strategies[self._state]()
        except Exception as e:
            self._logger.warn("UpdateServer is going down: " + str(e))
        finally:
            self._secure_socket.close()

    def _accept_connection(self):
        conn, address = self._secure_socket.accept()  # accept new connection
        self._logger.info("Connection from: " + str(address))
        try:
            connstream = self._tls_context.wrap_socket(conn, server_side=True)
        except ssl.SSLError as e:
            self._logger.warn("UpdateServer: " + str(e))
            return

        self._connection_to_dispatch = (connstream, address)
        self._state = ServerState.DISPATCH

    def _dispatch_connection(self):
        communicator = Thread(target=self._communicate,
                              args=self._connection_to_dispatch)
        communicator.setDaemon(True)
        communicator.start()
        self._connection_to_dispatch = None
        self._state = ServerState.ACCEPT

    def _communicate(self, connection: socket.socket, address):

        slave_nickname = connection.recv(1024).decode()
        connection.send(slave_nickname.encode())
        self._logger.debug("Successful handshake with %s" % str(slave_nickname))

        heartbeat_message_interval = 10
        counter = 0

        while not self._stop:
            data = connection.recv(1024).decode()
            if not data:
                self._logger.debug("Emtpy data from %s, closing" % str(slave_nickname))
                connection.close()
                break

            if counter == heartbeat_message_interval:
                counter = 0
            elif counter == 0:
                self._logger.debug("State update from %s of length %d" % (slave_nickname+" ("+address[0]+")", len(data)))
                counter += 1
            else:
                counter += 1

            self._latest_states[slave_nickname] = data

    def get_latest_state(self, slave_nickname):
        try:
            return self._latest_states[slave_nickname]
        except KeyError:
            return self._rm.get_string("slave_not_connected") % slave_nickname
