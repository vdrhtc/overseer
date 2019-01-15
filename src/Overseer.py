import subprocess

from telegram import *
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from threading import Lock
import pickle

from src.LoggingServer import LoggingServer
from src.ResourseManager import ResourceManager


class Overseer:

    def __init__(self, broadcaster):
        """

        :type broadcaster: src.Broadcaster.Broadcaster
        """
        self._broadcaster = broadcaster
        self._updater = broadcaster.get_telegram_updater()

        self._resource_manager = ResourceManager()
        self._lock = broadcaster.get_lock()

        start_handler = CommandHandler('start', self.on_start)
        scheme_handler = CommandHandler('scheme', self.on_scheme)
        sub_handler = CommandHandler('subscribe', self.on_subscribe)
        unsub_handler = CommandHandler('unsubscribe', self.on_unsubscribe)
        callback_handler = CallbackQueryHandler(self.on_callback)
        self._updater.dispatcher.add_handler(start_handler)
        self._updater.dispatcher.add_handler(scheme_handler)
        self._updater.dispatcher.add_handler(sub_handler)
        self._updater.dispatcher.add_handler(unsub_handler)
        self._updater.dispatcher.add_handler(callback_handler)

        self._logger = LoggingServer.getInstance()

    def launch(self):
        self._updater.start_polling()
        self._broadcaster.launch()

    def stop(self):
        self._broadcaster.stop()
        self._updater.stop()

    def stop_broadcaster(self):
        self._broadcaster.stop()

    def on_start(self, bot, update):
        update.message.reply_text(self._resource_manager.get_string("greeting"))

    def on_scheme(self, bot, update):
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="OK")]])
        with open("scheme.PNG", 'rb') as f:
            self._updater.bot.send_photo(update.message.chat_id, f, reply_markup=reply_markup)

    def on_subscribe(self, bot, update):

        try:
            client_ip = (update.message.text[11:])
        except IndexError:
            update.message.reply_text(self._resourceManager.getString("no_client_ip"))

        info_message_id = update.message.reply_text("Getting updates for %s..."%client_ip).message_id

        with self._lock:
            with open("resources/subscribers.pkl", "rb") as f:
                subscribers = pickle.load(f)

            try:
                ips = subscribers[update.message.chat_id][1]
                ips.add(client_ip)
                subscribers[update.message.chat_id] = (info_message_id, ips)
            except KeyError:
                ips = set()
                ips.add(client_ip)
                subscribers[update.message.chat_id] = (info_message_id, ips)

            with open("resources/subscribers.pkl", "wb") as f:
                pickle.dump(subscribers, f)

    def on_unsubscribe(self, bot, update):
        with self._lock:
            with open("resources/subscribers.pkl", "rb") as f:
                subscribers = pickle.load(f)

            del subscribers[update.message.chat_id]

            with open("resources/subscribers.pkl", "wb") as f:
                pickle.dump(subscribers, f)

    def on_callback(self, bot, update):
        if update.callback_query.data == "OK":
            self._updater.bot.deleteMessage(update.callback_query.message.chat_id,
                                            update.callback_query.message.message_id)

    def _check_tor(self):
        p1 = subprocess.Popen(["wmic", "process", "get", "description"], stdout=subprocess.PIPE)
        proc_names = [proc_name.strip() for proc_name in p1.communicate()[0].decode().split("\r\r\n")]
        if "tor.exe" not in proc_names:
            p1 = subprocess.Popen('"C:\\Users\\labiks\\Desktop\\Tor Browser\\Browser\\TorBrowser\\Tor\\tor.exe"',
                                  stdout=subprocess.PIPE)
