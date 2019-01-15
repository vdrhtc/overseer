import pickle
from threading import Lock, Thread
from time import sleep

from telegram import ParseMode


class Broadcaster:

    def __init__(self, telegram_updater, update_server):
        """

        :type update_server: src.UpdateServer.UpdateServer
        """
        self._lock = Lock()
        self._stop = False
        self._telegram_updater = telegram_updater
        self._update_server = update_server
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
                with self._lock:
                    with open("resources/subscribers.pkl", "rb") as f:
                        subscribers = pickle.load(f)
                for sub, params in subscribers.items():
                    print("\rSubs:", len(subscribers), ", updating", sub, end="", flush=True)

                    info_message_id, client_ips = params
                    for client_ip in client_ips:
                        message = self._update_server.get_latest_state(client_ip)
                        self._telegram_updater.bot.edit_message_text(message, sub, info_message_id,
                                                                     parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                print("\r", e, end="")
            sleep(15)
        self._running = False