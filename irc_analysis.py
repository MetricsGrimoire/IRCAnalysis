#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This script parses IRC logs and stores the extracted data in
# a database
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
# Note: Most of the source code of PlainIRCParser was taken from Marius Gedminas'
#   irclog2html.py tool, released under the terms of the GNU GPL.
#   See http://mg.pov.lt/irclog2html/ for more information.
#   Thanks to the author for this great tool
#

import io
import os
import sys
import re
from datetime import datetime
from optparse import OptionParser

from pyircanalysis.database import Database
from pyircanalysis.parsers import LogParser, PlainLogParser, HTMLLogParser


class Error(Exception):
    """Application error."""


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
    parser.add_option("-f", "--format",
                      type="choice",
                      action="store",
                      dest="logformat",
                      choices=["plain" , "html"],
                      help="Log file format")
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

    if len(args) != 0:
        parser.error("Wrong number of arguments")

    if not(opts.data_dir and opts.dbname and opts.dbuser and opts.channel and opts.logformat):
        parser.error("--dir --database --db-user and --channel --format are needed")
    return opts


DATE_FILENAME_REGEXP = re.compile(r'^(\d{4}\d{2}\d{2})(\.(.*))?$')
CHANNEL_FILENAME_REGEXP = re.compile(r'^#(.+)-(\d{4}-\d{2}-\d{2})(\.(.*))?$')

def parse_irc_filename(filename):
    """Test file name"""
    m = CHANNEL_FILENAME_REGEXP.match(filename)
    if m:
        return string_to_datetime(m.group(2), "%Y-%m-%d")

    m = DATE_FILENAME_REGEXP.match(filename)
    if m:
        return string_to_datetime(m.group(1), "%Y%m%d")
    raise Error("File name does not contain a valid date: %s" % filename)

def string_to_datetime(s, schema):
    """Convert string to datetime object"""
    try:
        return datetime.strptime(s, schema)
    except ValueError:
        raise Error("Parsing date %s to %s format" % (s, schema))

def parse_irc_file(filepath, channel_id, log_format, db, date_subs=None):
    """Parse a IRC log file."""
    try:
        infile = io.open(filepath, 'rt')
    except EnvironmentError as e:
        raise Error("Cannot open %s for reading: %s" % (filepath, e))

    count_msg = 0
    count_msg_new = 0
    last_date = db.get_last_date(opts.channel)

    try:
        if log_format == 'plain':
            parser = PlainLogParser(infile)
        else:
            parser = HTMLLogParser(infile)

        for date, what, info in parser:
            count_msg += 1

            # Replace log date by date_subs. Time remains the same.
            if date_subs:
                date = date.replace(year=date_subs.year,
                                    month=date_subs.month,
                                    day=date_subs.day)

            if (last_date and date <= last_date): continue
            if what == LogParser.COMMENT:
                nick, text = info
            else:
                if what == LogParser.NICKCHANGE:
                    text, oldnick, nick = info
                else:
                    text = info
                    nick = None

            db.insert_message(date, nick, text, channel_id)
            count_msg_new += 1
    except Exception as e:
        raise Error("Error parsing %s file: %s" % (filepath, e))
    finally:
        infile.close()
    return count_msg, count_msg_new


if __name__ == '__main__':
    opts = read_options()

    db = Database(opts.dbuser, opts.dbpassword, opts.dbname)
    db.open_database()
    db.create_tables()

    channel_id = db.get_channel_id(opts.channel)
    count_msg = count_msg_new = count_msg_drop = count_files_drop = 0

    files = os.listdir(opts.data_dir)
    files.sort()
    for logfile in files:
        try:
            date = parse_irc_filename(logfile)

            filepath = os.path.join(opts.data_dir, logfile)
            nmsg, nmsg_new = parse_irc_file(filepath, channel_id, opts.logformat,
                                            db, date)

            count_msg += nmsg
            count_msg_new += nmsg_new
        except Error as e:
            print(e)
            count_files_drop += 1
            continue

    db.close_database()
    print("Total messages: %s" % (count_msg))
    print("Total new messages: %s" % (count_msg_new))
    print("Total drop messages: %s" % (count_msg_drop))
    print("Total log files drop: %s" % (count_files_drop))
    sys.exit(0)