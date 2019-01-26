import pickle
from threading import Lock, Thread
from time import sleep

from telegram import ParseMode

from src.DBOperator import DBOperator


class Broadcaster:

    def __init__(self, telegram_updater, update_server, db_operator: DBOperator):
        """

        :type update_server: src.UpdateServer.UpdateServer
        """
        self._lock = Lock()
        self._stop = False
        self._telegram_updater = telegram_updater
        self._update_server = update_server
        self._db_operator = db_operator
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

    def _broadcast_updates(self):
        self._running = True
        while not self._stop:
            try:
                users = self._db_operator.get_users()
                for user in users:
                    print("\rSubs:", len(users), ", updating", user, end="", flush=True)

                    subscriptions = self._db_operator.get_subscriptions(user)
                    for subscription in subscriptions:
                        slave_nickname, info_message_id = subscription
                        message = self._update_server.get_latest_state(slave_nickname)
                        self._telegram_updater.bot.edit_message_text(message, user, info_message_id,
                                                                     parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                print("\r", e, end="")
            sleep(15)
        self._running = False