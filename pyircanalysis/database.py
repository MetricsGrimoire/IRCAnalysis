# -*- coding: utf-8 -*-
#
# Database storage module
#
# Copyright (C) 2012-2013 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#   Santiago Dueñas <sduenas@bitergia.com>
#   
#

import MySQLdb


class Database(object):

    def __init__(self, myuser, mypassword, mydb):
        self.myuser = myuser
        self.mypassword = mypassword
        self.mydb = mydb
        self.conn = None

    def open_database(self):
        conn = MySQLdb.Connect(host="127.0.0.1",
                               port=3306,
                               user=self.myuser,
                               passwd=self.mypassword,
                               db=self.mydb)
        self.conn = conn
        self.cursor = self.conn.cursor()

    def close_database(self):
        self.conn.close()

    # Management functions

    def create_tables(self):
        query = "CREATE TABLE IF NOT EXISTS irclog (" + \
                "id int(11) NOT NULL AUTO_INCREMENT," + \
                "nick VARCHAR(255) NULL," + \
                "date DATETIME NOT NULL," + \
                "message TEXT," + \
                "type VARCHAR(255) NULL," + \
                "channel_id int," + \
                "PRIMARY KEY (id)" + \
                ") ENGINE=MyISAM DEFAULT CHARSET=utf8"
        self.cursor.execute(query)

        query = "CREATE TABLE IF NOT EXISTS channels (" + \
                "id int(11) NOT NULL AUTO_INCREMENT," + \
                "name VARCHAR(255) NOT NULL," + \
                "PRIMARY KEY (id)" + \
                ") ENGINE=MyISAM DEFAULT CHARSET=utf8"
        self.cursor.execute(query)

        try:
            query = "DROP INDEX ircnick ON irclog;"
            self.cursor.execute(query)
        except MySQLdb.Error as e:
            print("Warning: Dropping nick index", e)

        try:
            query = "CREATE INDEX ircnick ON irclog (nick);"
            self.cursor.execute(query)
            self.conn.commit()
        except MySQLdb.Error as e:
            print("Warning: Creating nick index", e)

    def drop_tables(self):
        query = "DROP TABLE IF EXISTS irclog"
        self.cursor.execute(query)
        query = "DROP TABLE IF EXISTS channels"
        self.cursor.execute(query)

    # Queries (SELECT/INSERT) functions 

    def get_channel_id(self, name):
        query_s = "SELECT * FROM channels WHERE name = %s"
        self.cursor.execute(query_s, (name))
        results =  self.cursor.fetchall()
        if len(results) == 0:
            query_i = "INSERT INTO channels (name) VALUES (%s)"
            self.cursor.execute(query_i, (name))
            self.conn.commit()
            self.cursor.execute(query_s, (name))
            results =  self.cursor.fetchall()
        channel_id = str(results[0][0])
        return channel_id

    def get_last_date(self, channel_id):
        query =  "SELECT MAX(date) FROM irclog, channels "
        query += "WHERE irclog.channel_id=channels.id "
        query += "AND channels.id = %s"
        self.cursor.execute(query, (channel_id))
        return self.cursor.fetchone()[0]

    def insert_message(self, date, nick, message, message_type, channel_id):
        query =  "INSERT INTO irclog (date, nick, message, type, channel_id) "
        query += "VALUES (%s, %s, %s, %s, %s)"
        self.cursor.execute(query, (date, self._escape(nick),
                                    self._escape(message), message_type,
                                    channel_id))
        self.conn.commit()

    def _escape(self, s):
        if not s:
            return None
        return self.conn.escape_string(s)
