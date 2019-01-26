import socket
from queue import Queue
from threading import Thread, Lock

from src.LoggingServer import LoggingServer


class UpdateServer:

    def __init__(self):

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
        self._logger.debug("UpdateServer: listening on %s" % str((self._host, self._port)))

        connection_dispatcher = Thread(target=self._dispatch_connections)
        connection_dispatcher.setDaemon(True)
        connection_dispatcher.start()

    def stop(self):
        self._stop = True

    def _dispatch_connections(self):
        while not self._stop:
            conn, address = self._socket.accept()  # accept new connection
            self._logger.debug("Connection from: " + str(address))
            # print("Connection from: " + str(address))

            communicator = Thread(target=self._communicate, args=[conn, address])
            communicator.setDaemon(True)
            communicator.start()
        self._socket.close()

    def _communicate(self, connection: socket.socket, address):
        while not self._stop:
            data = connection.recv(1024).decode()
            if not data:
                self._logger.debug("Emtpy data from %s, closing" % str(address))
                connection.close()
                break

            self._logger.debug("State update from %s of length %d" % (address[0], len(data)))
            # print("State update from %s of length %d" % (address, len(data)))
            self._latest_states[address[0]] = data

    def get_latest_state(self, address):
        try:
            return self._latest_states[address]
        except KeyError:
            return "Address %s has not yet connected!" % address
