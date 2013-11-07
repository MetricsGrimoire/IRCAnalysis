#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
# Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

from optparse import OptionParser
import os, sys
from datetime import datetime

from pyircanalysis.database import Database


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


if __name__ == '__main__':
    opts = None
    opts = read_options()
    db = Database(opts.dbuser, opts.dbpassword, opts.dbname)
    db.open_database()

    db.create_tables()
    channel_id = db.get_channel_id(opts.channel)
    last_date = db.get_last_date(opts.channel)

    count_msg = count_msg_new = count_msg_drop = count_files_drop = 0
    files = os.listdir(opts.data_dir)
    for logfile in files:
        year = logfile[0:4]
        month = logfile[4:6]
        day = logfile[6:8]    
        date = year + "-" + month + "-" + day
        try:
            date_test = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            count_files_drop += 1
            print "Bad filename format in  " + logfile
            continue

        date_nick_msg = parse_file(opts.data_dir + "/" + logfile)

        for i in date_nick_msg:
            count_msg += 1
            # date: 2013-07-11 15:39:16
            date_time = date + " " + i[0]
            try:
                msg_date = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                count_msg_drop += 1
                print "Bad format in " + date_time + " (" + logfile + ")"
                continue
            if (last_date and msg_date <= last_date): continue
            db.insert_message(date_time, i[1], i[2], channel_id)
            count_msg_new += 1
            if (count_msg % 1000 == 0): print (count_msg)

    db.close_database()
    print("Total messages: %s" % (count_msg))
    print("Total new messages: %s" % (count_msg_new))
    print("Total drop messages: %s" % (count_msg_drop))
    print("Total log files drop: %s" % (count_files_drop))
    sys.exit(0)