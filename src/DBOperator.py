from datetime import datetime

import psycopg2
from psycopg2 import ProgrammingError, IntegrityError
from psycopg2.extras import Inet
from telegram import Message
from collections import namedtuple


class DBOperator:
    TABLES = ["users", "slaves", "subscriptions", "messages"]

    def __init__(self, dbname, user, password, drop_key=""):
        self._dbname = dbname
        self._user = user
        self._password = password

        self._conn = psycopg2.connect("dbname=%s user=%s password=%s" % (dbname, user, password))
        self._c = self._conn.cursor()

        if drop_key == "r4jYi1@" and dbname == "overseer_test":
            for table in self.TABLES:
                try:
                    with self._conn:
                        self._c.execute("DROP TABLE %s CASCADE;" % table)
                except ProgrammingError as e:
                    print(e)

        if len(self.get_tables()) == 0:
            self.create_tables()

    def get_tables(self):
        with self._conn:
            query = """SELECT table_name 
                       FROM information_schema.tables 
                       WHERE table_schema = 'public' 
                       ORDER BY table_schema,table_name;"""
            self._c.execute(query)
            return self._c.fetchall()

    def create_tables(self):
        with self._conn:
            query = """
                    CREATE TABLE users (
                        user_id serial PRIMARY KEY,
                        telegram_id integer UNIQUE NOT NULL,
                        full_name VARCHAR(50),
                        nickname VARCHAR(50)
                    );
                    """
            self._c.execute(query)

            query = """
                    CREATE TABLE slaves (
                        slave_id serial PRIMARY KEY,
                        slave_nickname VARCHAR(50) UNIQUE NOT NULL,
                        slave_ip inet
                    );
                    """
            self._c.execute(query)

            query = """
                    CREATE TABLE subscriptions (
                        user_id integer NOT NULL,
                        slave_id integer NOT NULL,
                        sub_date timestamp without time zone,
                        info_message_id integer,
                        
                        PRIMARY KEY (user_id, slave_id),
                        CONSTRAINT subscriptions_role_id_fkey FOREIGN KEY (user_id)
                            REFERENCES users (user_id) MATCH SIMPLE
                            ON UPDATE CASCADE ON DELETE CASCADE,
                        CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (slave_id)
                            REFERENCES slaves (slave_id) MATCH SIMPLE
                             ON UPDATE CASCADE ON DELETE CASCADE
                    );
                    """
            self._c.execute(query)

            query = """
                    CREATE TABLE messages (
                        user_telegram_id integer NOT NULL,
                        message_id integer NOT NULL,
                        user_full_name VARCHAR(250) NOT NULL,
                        user_telegram_nick VARCHAR(250) NOT NULL,
                        date timestamp without time zone,
                        text VARCHAR(6000)

                    );
                    CREATE INDEX messages_idx ON messages (user_telegram_id, message_id);
                    """
            self._c.execute(query)

    def add_user(self, user):
        telegram_id = user.id
        full_name = user.full_name
        nickname = user.name
        try:
            query = "INSERT INTO users (telegram_id, full_name, nickname) VALUES (%s, %s, %s);"
            self._c.execute(query, [telegram_id, full_name, nickname])
            self._conn.commit()
        except IntegrityError:
            self._conn.rollback()  # user is already known
            query = "UPDATE users SET (full_name, nickname) = (%s, %s) WHERE telegram_id = %s;"
            self._c.execute(query, [full_name, nickname, telegram_id])
            self._conn.commit()



    def add_slave(self, slave):
        slave_nickname = slave.nickname
        slave_ip = slave.ip
        try:
            query = "INSERT INTO slaves (slave_nickname, slave_ip) VALUES (%s, %s);"
            self._c.execute(query, [slave_nickname, Inet(slave_ip)])
            self._conn.commit()
        except IntegrityError:
            self._conn.rollback()  # slave is already known

    def get_users(self):
        fields = "telegram_id", "full_name", "nickname"
        with self._conn:
            self._c.execute("select %s from users" % ", ".join(fields))
            raw_users = self._c.fetchall()
            users = []
            for raw_user in raw_users:
                User = namedtuple("User", fields)
                users.append(User(*raw_user))
            return users

    def get_slaves(self):
        with self._conn:
            fields = "slave_nickname", "slave_ip"
            self._c.execute("select %s from slaves" % ", ".join(fields))
            raw_slaves = self._c.fetchall()
            slaves = []
            for raw_slave in raw_slaves:
                Slave = namedtuple("Slave", fields)
                slaves.append(Slave(*raw_slave))
            return slaves

    def get_subscriptions(self, telegram_id):

        with self._conn:
            query = """SELECT slave_nickname, info_message_id
                          FROM slaves
                        LEFT OUTER JOIN subscriptions
                          ON slaves.slave_id = subscriptions.slave_id
                        LEFT OUTER JOIN users
                          ON users.user_id = subscriptions.user_id
                        where telegram_id = %s;
                    """
            self._c.execute(query, [telegram_id])
            return self._c.fetchall()

    def subscribe(self, telegram_id, slave_nickname, info_message_id):

        user_id = self._get_user_id(telegram_id)
        slave_id = self._get_slave_id(slave_nickname)
        sub_date = datetime.now()

        try:
            query = "INSERT INTO subscriptions (user_id, slave_id, sub_date, info_message_id) VALUES (%s, %s, %s, %s);"
            self._c.execute(query, [user_id, slave_id, sub_date, info_message_id])
            self._conn.commit()
        except IntegrityError:  # user is already subscribed to slave
            self._conn.rollback()
            with self._conn:
                query = "UPDATE subscriptions SET info_message_id = %s, sub_date = %s WHERE user_id = %s AND slave_id = %s"
                self._c.execute(query, [info_message_id, sub_date, user_id, slave_id])

    def unsubscribe(self, telegram_id, slave_nickname):

        user_id = self._get_user_id(telegram_id)
        slave_id = self._get_slave_id(slave_nickname)

        try:
            query = "DELETE FROM subscriptions WHERE user_id=%s AND slave_id=%s;"
            self._c.execute(query, [user_id, slave_id])
            self._conn.commit()
        except ProgrammingError as e:
            self._conn.rollback()
            raise ValueError("Delete error: %s" % str(e))

    def add_message(self, message: Message):
        user_telegram_id = message.from_user.id
        message_id = message.message_id
        user_full_name = message.from_user.full_name
        user_telegram_nick = message.from_user.name
        date = message.date
        text = message.text

        fields = [user_telegram_id, message_id, user_full_name,
                  user_telegram_nick, date, text]

        with self._conn:
            query = "INSERT INTO messages (user_telegram_id, message_id, user_full_name, " \
                    "                      user_telegram_nick, date, text) " \
                    "VALUES (%s, %s, %s, %s, %s, %s);"
            self._c.execute(query, fields)

    def get_messages(self, telegram_id):
        with self._conn:
            query = "SELECT * from messages WHERE user_telegram_id = %s"
            self._c.execute(query, [telegram_id])
            return self._c.fetchall()

    def _get_user_id(self, telegram_id):
        try:
            self._c.execute("select users.user_id from users where users.telegram_id = %s", [telegram_id])
            return self._c.fetchall()[0][0]
        except IndexError:
            self._conn.rollback()
            raise ValueError("User %d not found" % telegram_id)

    def _get_slave_id(self, slave_nickname):
        try:
            self._c.execute("select slaves.slave_id from slaves where slaves.slave_nickname=%s", [slave_nickname])
            return self._c.fetchall()[0][0]
        except IndexError:
            self._conn.rollback()
            raise ValueError("Slave %s not found" % slave_nickname)
