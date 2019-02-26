import socket
from queue import Queue
from threading import Thread, Lock

from src.LoggingServer import LoggingServer
from src.ResourceManager import ResourceManager


class UpdateServer:

    def __init__(self):

        self._rm = ResourceManager()
        self._host = "0.0.0.0"
        self._port = 5000  # initiate port no above 1024
        self._stop = False
        self._socket = None
        self._logger = LoggingServer.getInstance()

        self._latest_states = {}

    def launch(self):

        self._stop = False
        self._socket = socket.socket()
        self._socket.bind((self._host, self._port))
        self._socket.listen()
        self._logger.info("UpdateServer: listening on %s" % str((self._host, self._port)))

        connection_dispatcher = Thread(target=self._dispatch_connections)
        connection_dispatcher.setDaemon(True)
        connection_dispatcher.start()

    def stop(self):
        self._stop = True

    def _dispatch_connections(self):
        while not self._stop:
            conn, address = self._socket.accept()  # accept new connection
            self._logger.info("Connection from: " + str(address))
            # print("Connection from: " + str(address))

            communicator = Thread(target=self._communicate, args=[conn, address])
            communicator.setDaemon(True)
            communicator.start()
        self._socket.close()

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
