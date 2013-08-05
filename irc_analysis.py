#!/usr/bin/python
# -*- coding: utf-8 -*-

# This script parse IRC logs from Wikimedia 
# and store them in database

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
# This file is a part of the VizGrimoireJS package
#
# Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

from optparse import OptionParser
import os, sys
import MySQLdb


def read_file(filename):
    fd = open(filename, "r")
    lines = fd.readlines()
    fd.close()
    return lines


def parse_file(filename):
    date_nick_message = []
    lines = read_file(filename)
    for l in lines:
        # [12:39:15] <wm-bot>  Infobot disabled
        aux = l.split(" ")
        time = aux[0]
        time = time[1:len(time) - 1]
        nick = (aux[1].split("\t"))[0]
        nick = nick[1:len(nick) - 1]
        msg = ' '.join(aux[2:len(aux)])
        date_nick_message.append([time, nick, msg])
    return date_nick_message


def open_database(myuser, mypassword, mydb):
    con = MySQLdb.Connect(host="127.0.0.1",
                          port=3306,
                          user=myuser,
                          passwd=mypassword,
                          db=mydb)
    # cursor = con.cursor()
    # return cursor
    return con


def close_database(con):
    con.close()


def read_options():
    parser = OptionParser(usage="usage: %prog [options]",
                          version="%prog 0.1")
    parser.add_option("--dir",
                      action="store",
                      dest="data_dir",
                      default="irc",
                      help="Directory with all IRC logs")
    parser.add_option("--channel",
                      action="store",
                      dest="channel",
                      help="Channel name")    
    parser.add_option("-d", "--database",
                      action="store",
                      dest="dbname",
                      help="Database where identities table is stored")
    parser.add_option("--db-user",
                      action="store",
                      dest="dbuser",
                      default="root",
                      help="Database user")
    parser.add_option("--db-password",
                      action="store",
                      dest="dbpassword",
                      default="",
                      help="Database password")
    parser.add_option("-g", "--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="Debug mode")
    (opts, args) = parser.parse_args()
    # print(opts)
    if len(args) != 0:
        parser.error("Wrong number of arguments")

    if not(opts.data_dir and opts.dbname and opts.dbuser and opts.channel):
        parser.error("--dir --database --db-user and --channel are needed")
    return opts

def escape_string (message):
    if "\\" in message:
        message = message.replace("\\", "\\\\")
    if "'" in message:    
        message = message.replace("'", "\\'")
    return message
 

def insert_message(cursor, date, nick, message, channel_id):
    message = escape_string (message)
    nick = escape_string (nick)
    q = "insert into irclog (date,nick,message,channel_id) values (";
    q += "'" + date + "','" + nick + "','" + message + "','"+channel_id+"')"
    cursor.execute(q)
    
def create_tables(cursor, con):
#    query = "DROP TABLE IF EXISTS irclog"
#    cursor.execute(query)
#    query = "DROP TABLE IF EXISTS channels"
#    cursor.execute(query)

    query = "CREATE TABLE IF NOT EXISTS irclog (" + \
           "id int(11) NOT NULL AUTO_INCREMENT," + \
           "nick VARCHAR(255) NOT NULL," + \
           "date DATETIME NOT NULL," + \
           "message TEXT," + \
           "channel_id int," + \
           "PRIMARY KEY (id)" + \
           ") ENGINE=MyISAM DEFAULT CHARSET=utf8"
    cursor.execute(query)
    
    query = "CREATE TABLE IF NOT EXISTS channels (" + \
           "id int(11) NOT NULL AUTO_INCREMENT," + \
           "name VARCHAR(255) NOT NULL," + \
           "PRIMARY KEY (id)" + \
           ") ENGINE=MyISAM DEFAULT CHARSET=utf8"
    cursor.execute(query)
    
    try:
        query = "DROP INDEX ircnick ON irclog;"
        cursor.execute(query)
        query = "CREATE INDEX ircnick ON irclog (nick);"
        cursor.execute(query)
        con.commit()
    except MySQLdb.Error:
        print "Problems creating nick index"

    return


if __name__ == '__main__':
    opts = None
    opts = read_options()
    # ids_file = parse_file(opts.countries_file)
    con = open_database(opts.dbuser, opts.dbpassword, opts.dbname)
        
    
    cursor = con.cursor()
    create_tables(cursor, con)
    
    query = "INSERT INTO channels (name) VALUES ('"+opts.channel+"')"
    cursor.execute(query)
    query = "SELECT MAX(id) FROM channels limit 1"
    cursor.execute(query)
    channel_id = str(cursor.fetchall()[0][0])
    
    count_msg = 0
    files = os.listdir(opts.data_dir)
    for logfile in files:
        year = logfile[0:4]
        month = logfile[4:6]
        day = logfile[6:8]    
        date = year + "-" + month + "-" + day
        date_nick_msg = parse_file(opts.data_dir + "/" + logfile)

        for i in date_nick_msg:
            insert_message (cursor, date + " " + i[0], i[1], i[2], channel_id)                
            count_msg += 1
            if (count_msg % 1000 == 0): print (count_msg)
        con.commit()

    close_database(con)
    print("Total messages: %s" % (count_msg))
    sys.exit(0)