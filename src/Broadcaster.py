import pickle
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from telegram import ParseMode
from telegram.error import BadRequest, TimedOut, NetworkError
from telegram.ext import Updater, run_async

from src.DBOperator import DBOperator
from loggingserver import LoggingServer
from src.ResourceManager import ResourceManager


class Broadcaster:

    def __init__(self, telegram_updater: Updater, update_server, db_operator: DBOperator):
        """

        :type update_server: src.UpdateServer.UpdateServer
        """
        self._logger = LoggingServer.getInstance("overseer-broadcaster")
        self._stop = False
        self._telegram_updater = telegram_updater
        self._update_server = update_server
        self._db_operator = db_operator
        self._resource_manager = ResourceManager()
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=32)

    def get_telegram_updater(self):
        return self._telegram_updater

    def get_lock(self):
        return self._lock

    def launch(self):
        if self._running:
            raise ValueError("Already running!")

        self._update_server.launch()

        self._stop = False
        t = Thread(target=self._run)
        t.setDaemon(True)
        t.start()

    def stop(self):
        self._update_server.stop()
        self._stop = True

    def get_update_server(self):
        return self._update_server

    def _run(self):
        self._running = True
        while not self._stop:
            self._broadcast_updates()
            sleep(15)
        self._running = False

    def _broadcast_updates(self):

        user_sub_pairs = []

        users = self._db_operator.get_users()
        for user in users:
            for subscription in self._db_operator.get_subscriptions(user.telegram_id):
                user_sub_pairs.append((user, subscription))

        for result in self._executor.map(self._send_update, user_sub_pairs):
            user, subscription, error = result
            print("\rUpdated %s, slave: %s. Error: %s" % (str(user.full_name), str(subscription[0]), str(error)),
                  end=" " * 10, flush=True)

    def _send_update(self, target):

        user, subscription = target

        slave_nickname, info_message_id = subscription
        message = self._update_server.get_latest_state(slave_nickname)



        try:
            self._telegram_updater.bot.edit_message_text(message,
                                                         user.telegram_id,
                                                         info_message_id,
                                                         parse_mode=ParseMode.MARKDOWN)
            return user, subscription, None
        except BadRequest as e:
            if message != self._resource_manager.get_string("slave_not_connected") % slave_nickname:
                if e.message != "Message is not modified":
                    self._logger.warn("Error for user %d, %s: " % (user.telegram_id, slave_nickname) + str(e))
            return user, subscription, e
        except TimedOut as e:
            self._logger.warn("Timed out updating %d, %s" % (user.telegram_id, slave_nickname))
            return user, subscription, e
        except NetworkError as e:
            self._logger.warn("Network error %d, %s: " % (user.telegram_id, slave_nickname) + str(e))
            return user, subscription, e

