import datetime
import socket
import ssl
from enum import Enum, auto
from hashlib import md5
from loggingserver import LoggingServer
from threading import Thread

from src.DBOperator import DBOperator
from src.ResourceManager import ResourceManager
from src.SlaveState import SlaveState


class ServerState(Enum):
    ACCEPT = auto()
    DISPATCH = auto()


class UpdateServer:

    def __init__(self, tls_context, db_operator: DBOperator):

        self._db_operator = db_operator

        self._rm = ResourceManager()
        self._host = "0.0.0.0"
        self._port = 5000  # initiate port no above 1024
        self._secure_port = 5000
        self._stop = False
        self._socket = None

        self._secure_socket = None
        self._tls_context = tls_context

        self._logger = LoggingServer.getInstance("overseer")

        self._latest_states = {}

        self._strategies = {ServerState.ACCEPT: self._accept_connection,
                            ServerState.DISPATCH: self._dispatch_connection}
        self._state = ServerState.ACCEPT

        self._connection_to_dispatch = None

        self._heartbeat_message_interval = 10
        self._heartbeat_interval_counters = {}


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
            self._logger.warn("UpdateServer is going down: " + str(e) +
                              repr(e) + str(type(e)))
            self._stop = True
        finally:
            self._secure_socket.close()

    def _accept_connection(self):
        try:
            conn, address = self._secure_socket.accept()  # accept new connection
            self._logger.info("Connection from: " + str(address))
            connstream = self._tls_context.wrap_socket(conn, server_side=True)
        except (ssl.SSLError, ConnectionError, socket.error) as e:
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

    def _authenticate_slave(self, nickname, password):
        slave = self._db_operator.get_slave(nickname)

        md5_pass = md5(password.encode()).hexdigest()
        if slave.slave_password == md5_pass and password != "":
            return True

        return False

    def _communicate(self, connection: socket.socket, address):

        try:
            slave_nickname, slave_password = connection.recv(1024).decode().split("\r\n")

            if not self._authenticate_slave(slave_nickname, slave_password):
                raise ValueError("Wrong username/password!")

        except ValueError as e:
            self._logger.warn("Authentication failed, %s" % str(e))
            connection.send(("Authentication failed: " + e.args[0]).encode())
            return

        connection.send(slave_nickname.encode())
        self._logger.debug("Successful handshake with %s" % str(slave_nickname))

        self._heartbeat_interval_counters[slave_nickname] = 0

        for data in self._update_generator(connection, slave_nickname):
            self._latest_states[slave_nickname] = SlaveState(slave_nickname, data)
            self._log_heartbeat(slave_nickname, address, len(data))

        connection.close()

    def _update_generator(self, connection, slave_nickname):
        data = connection.recv(1024).decode()

        while data != "" and not self._stop:
            yield data
            data = connection.recv(1024).decode()

        if data == "":
            self._logger.debug("Emtpy data from %s, closing" % str(slave_nickname))

    def _log_heartbeat(self, slave_nickname, address, length):
        if self._heartbeat_interval_counters[slave_nickname] %\
                self._heartbeat_message_interval == 0:
            self._logger.debug("State update from %s (%s) of length %d" %
                               (slave_nickname, address[0], length))
            self._heartbeat_interval_counters[slave_nickname] = 0

        self._heartbeat_interval_counters[slave_nickname] += 1

    def get_latest_state(self, slave_nickname):
        try:
            return self._latest_states[slave_nickname]
        except KeyError:
            return SlaveState(slave_nickname,
                              self._rm.get_string("slave_not_connected") % slave_nickname)
