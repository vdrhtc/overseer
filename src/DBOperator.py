from datetime import datetime

import psycopg2
from psycopg2 import ProgrammingError, IntegrityError
from psycopg2.extras import Inet


class DBOperator:

    def __init__(self, dbname, user, password):
        self._dbname = dbname
        self._user = user
        self._password = password

        self._conn = psycopg2.connect("dbname=%s user=%s password=%s" % (dbname, user, password))
        self._c = self._conn.cursor()

    def create_tables(self):
        try:
            query = """
                    CREATE TABLE users (
                        user_id serial PRIMARY KEY,
                        telegram_id integer UNIQUE NOT NULL
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

            self._conn.commit()
        except ProgrammingError as e:
            print(e)
            self._conn.rollback()

    def add_user(self, telegram_id: int):
        with self._conn:
            query = "INSERT INTO users (telegram_id) VALUES (%s);"
            self._c.execute(query, [telegram_id])
            self._conn.commit()

    def add_slave(self, nickname, ip):
        with self._conn:
            query = "INSERT INTO slaves (slave_nickname, slave_ip) VALUES (%s, %s);"
            self._c.execute(query, [nickname, Inet(ip)])
            self._conn.commit()

    def get_users(self):
        with self._conn:
            self._c.execute("select * from users")
            return self._c.fetchall()

    def get_slaves(self):
        with self._conn:
            self._c.execute("select * from slaves")
            return self._c.fetchall()

    def get_subscriptions(self, telegram_id):
        
        user_id = self._get_user_id(telegram_id)
        
        with self._conn:
            query = """SELECT slave_nickname FROM slaves WHERE slave_id IN (
                          SELECT slave_id FROM users JOIN subscriptions USING (user_id) 
                             WHERE user_id=%s
                          );"""
            self._c.execute(query, [user_id])
            return self._c.fetchall()

    def subscribe(self, telegram_id, slave_nickname):

        user_id = self._get_user_id(telegram_id)
        slave_id = self._get_slave_id(slave_nickname)

        try:
            sub_date = datetime.now()

            query = "INSERT INTO subscriptions (user_id, slave_id, sub_date) VALUES (%s, %s, %s);"
            self._c.execute(query, [user_id, slave_id, sub_date])
            self._conn.commit()
        except IntegrityError:
            self._conn.rollback()
            raise ValueError("User %d is already subscribed to slave %s" % (telegram_id, slave_nickname))

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
