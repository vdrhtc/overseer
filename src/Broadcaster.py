import pickle
from threading import Lock, Thread
from time import sleep

from telegram import ParseMode
from telegram.error import BadRequest, TimedOut, NetworkError
from telegram.ext import Updater

from src.DBOperator import DBOperator
from src.LoggingServer import LoggingServer
from src.ResourceManager import ResourceManager


class Broadcaster:

    def __init__(self, telegram_updater: Updater, update_server, db_operator: DBOperator):
        """

        :type update_server: src.UpdateServer.UpdateServer
        """
        self._lock = Lock()
        self._logger = LoggingServer.getInstance()
        self._stop = False
        self._telegram_updater = telegram_updater
        self._update_server = update_server
        self._db_operator = db_operator
        self._resource_manager = ResourceManager()
        self._running = False

    def get_telegram_updater(self):
        return self._telegram_updater

    def get_lock(self):
        return self._lock

    def launch(self):
        if self._running:
            raise ValueError("Already running!")

        self._update_server.launch()

        self._stop = False
        t = Thread(target=self._broadcast_updates)
        t.setDaemon(True)
        t.start()

    def stop(self):
        self._update_server.stop()
        self._stop = True

    def get_update_server(self):
        return self._update_server

    def _broadcast_updates(self):
        self._running = True
        while not self._stop:
            users = self._db_operator.get_users()
            for user in users:

                subscriptions = self._db_operator.get_subscriptions(user)
                print("\rSubs:", len(subscriptions), ", updating", user, end="", flush=True)

                for subscription in subscriptions:
                    slave_nickname, info_message_id = subscription
                    message = self._update_server.get_latest_state(slave_nickname)
                    try:
                        self._telegram_updater.bot.edit_message_text(message, user, info_message_id,
                                                                     parse_mode=ParseMode.MARKDOWN)
                    except BadRequest as e:
                        self._logger.warn("Error for user %d, %s: " % (user, slave_nickname) + str(e))
                    except TimedOut as e:
                        self._logger.warn("Timed out updating %d, %s: " % (user, slave_nickname) + str(e))
                    except NetworkError as e:
                        self._logger.warn("Network error %d, %s: " % (user, slave_nickname) + str(e))

            sleep(15)
        self._running = False
