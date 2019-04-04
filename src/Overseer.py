import subprocess
from collections import namedtuple

from telegram import *
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from threading import Lock
import pickle

from src.DBOperator import DBOperator
from src.LoggingServer import LoggingServer
from src.ResourceManager import ResourceManager

from src.LoggingServer import LoggingServer
from enum import Enum, auto


class SlaveRegistrationStages(Enum):
    SLAVE_NAME = auto()
    SLAVE_PASS = auto()


def record_message(callback):
    def wrapper(*args):
        self, bot, update = args
        self._db_operator.add_message(update.message)
        callback(*args)

    return wrapper


class Overseer:

    def __init__(self, broadcaster, db_operator: DBOperator):
        """

        :type broadcaster: src.Broadcaster.Broadcaster
        """
        self._broadcaster = broadcaster
        self._db_operator = db_operator
        self._updater = broadcaster.get_telegram_updater()

        self._resource_manager = ResourceManager()
        self._logger = LoggingServer.getInstance()

        self._updater.dispatcher.add_handler(CommandHandler('start', self.on_start))
        self._updater.dispatcher.add_handler(CommandHandler('help', self.on_help))
        self._updater.dispatcher.add_handler(CommandHandler('scheme', self.on_scheme))
        self._updater.dispatcher.add_handler(CommandHandler('checkout', self.on_checkout))
        self._updater.dispatcher.add_handler(CommandHandler('subscribe', self.on_subscribe))
        self._updater.dispatcher.add_handler(CommandHandler('unsubscribe', self.on_unsubscribe))
        self._updater.dispatcher.add_handler(CommandHandler('register_slave', self.on_register_slave))

        self._updater.dispatcher.add_handler(MessageHandler(Filters.text, callback=self.on_message))
        self._updater.dispatcher.add_handler(CallbackQueryHandler(self.on_callback))
        self._message_filters = [self._filter_slave_registration]

        self._logger = LoggingServer.getInstance()

        self._slave_registration_conversations = {}
        self._slave_registration_data = {}
        self._slave_registration_functions = {SlaveRegistrationStages.SLAVE_NAME: self._register_slave_name,
                                              SlaveRegistrationStages.SLAVE_PASS: self._register_slave_password}

    def launch(self):
        self._updater.start_polling()
        self._broadcaster.launch()

    def stop(self):
        self._broadcaster.stop()
        self._updater.stop()

    def stop_broadcaster(self):
        self._broadcaster.stop()

    @record_message
    def on_start(self, bot, update):
        self._log_user_action("/start", update.message.from_user)

        update.message.reply_text(self._resource_manager.get_string("greeting"))

    @record_message
    def on_help(self, bot, update):
        self._log_user_action("/help", update.message.from_user)

        with open("resources/command_summary.html", "r") as f:
            update.message.reply_text(f.read(), parse_mode="HTML")

    @record_message
    def on_scheme(self, bot, update):
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="OK")]])
        with open("scheme.PNG", 'rb') as f:
            self._updater.bot.send_photo(update.message.chat_id, f, reply_markup=reply_markup)

    @record_message
    def on_subscribe(self, bot, update):
        self._log_user_action("/subscribe", update.message.from_user)
        slave_nickname = update.message.text[11:]

        if slave_nickname == "":
            update.message.reply_text(self._resource_manager.get_string("no_slave_nickname"))
            return

        user_telegram_id = update.message.chat_id

        try:
            self._db_operator.get_slave(slave_nickname)
        except ValueError:
            update.message.reply_text(self._resource_manager.get_string("no_slave"))
            return

        self._logger.info("Subscribing user %d to slave %s" % (user_telegram_id, slave_nickname))

        self._db_operator.add_user(update.message.from_user)
        # Slave = namedtuple("Slave", "nickname ip owner password")
        # self._db_operator.add_slave(Slave(slave_nickname, None, user_telegram_id, ))

        info_message_id = update.message.reply_text(self._resource_manager
                                                    .get_string("fetching_updates") % slave_nickname).message_id

        self._db_operator.subscribe(user_telegram_id, slave_nickname, info_message_id)

    @record_message
    def on_checkout(self, bot, update):
        self._log_user_action("/checkout", update.message.from_user)

        slave_nickname = update.message.text[10:]
        if slave_nickname == "":
            update.message.reply_text(self._resource_manager.get_string("no_slave_nickname"))
            return

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data="OK")]])
        update.message.reply_text(self._broadcaster.get_update_server().get_latest_state(slave_nickname),
                                  parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    @record_message
    def on_unsubscribe(self, bot, update):
        self._log_user_action("/unsubscribe", update.message.from_user)

        user_telegram_id = update.message.chat_id
        slave_nickname = update.message.text[13:]

        if slave_nickname == "":
            update.message.reply_text(self._resource_manager.get_string("no_slave_nickname"))
            return

        self._logger.info("Unsubscribing user %d from slave %s" % (user_telegram_id, slave_nickname))

        self._db_operator.unsubscribe(user_telegram_id, slave_nickname)
        update.message.reply_text(self._resource_manager.get_string("unsubscribed") % slave_nickname)

    def on_callback(self, bot, update):
        if update.callback_query.data == "OK":
            self._updater.bot.deleteMessage(update.callback_query.message.chat_id,
                                            update.callback_query.message.message_id)

    @record_message
    def on_register_slave(self, bot, update):
        self._log_user_action("/register_slave", update.message.from_user)
        self._slave_registration_conversations[update.message.from_user.id] = SlaveRegistrationStages.SLAVE_NAME
        update.message.reply_text(self._resource_manager.get_string("slave_registration_started"))

    def on_message(self, bot, update):
        self._log_user_action("A message was received", update.message.from_user)
        for message_filter in self._message_filters:
            update = message_filter(update)
            if update is None:
                return  # update consumed

    def _filter_slave_registration(self, update):
        conversations = self._slave_registration_conversations
        user_id = update.message.from_user.id
        if user_id in conversations.keys():
            conversations[user_id] = self._slave_registration_functions[conversations[user_id]](update)
            if conversations[user_id] is None:
                self._log_user_action("New slave %s registered" % self._slave_registration_data[user_id],
                                      update.message.from_user)
                del self._slave_registration_data[user_id]
                del self._slave_registration_conversations[user_id]
                update.message.reply_text(self._resource_manager.get_string("slave_registered"))
        else:
            return update

    def _register_slave_name(self, update):
        slave_name = update.message.text

        self._slave_registration_data[update.message.from_user.id] = slave_name

        self._log_user_action("Slave name %s received for registration" % slave_name, update.message.from_user)
        try:
            Slave = namedtuple("Slave", "nickname ip owner password")
            self._db_operator.add_slave(Slave(slave_name, "0.0.0.0", update.message.from_user.id, ""))
            update.message.reply_text(self._resource_manager.get_string("slave_registration_password"))
        except ValueError as e:
            self._logger.debug("Slave name invalid: %s" % e.args[0])
            update.message.reply_text(e.args[0])
            return SlaveRegistrationStages.SLAVE_NAME
        else:
            return SlaveRegistrationStages.SLAVE_PASS

    def _register_slave_password(self, update):
        user_id = update.message.from_user.id
        slave_pass = update.message.text
        slave_name = self._slave_registration_data[user_id]
        self._log_user_action("Slave password received for registration", update.message.from_user)
        try:
            Slave = namedtuple("Slave", "nickname ip owner password")
            self._db_operator.update_slave(Slave(slave_name, "0.0.0.0",
                                                 user_id, slave_pass))
        except ValueError as e:
            update.message.reply_text(e.args[0])
            return SlaveRegistrationStages.SLAVE_PASS

    def _log_user_action(self, msg, user):
        self._logger.debug("%s, user: %s, %d" % (msg, user.full_name, user.id))
