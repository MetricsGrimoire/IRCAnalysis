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

import calendar
import io
import logging
import requests
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
    parser.add_option("-c", "--channel",
                      action="store",
                      dest="channel",
                      help="Channel name")
    parser.add_option("-f", "--format",
                      type="choice",
                      action="store",
                      dest="logformat",
                      choices=["plain" , "html", "slack"],
                      help="Log file format")
    parser.add_option("-d", "--database",
                      action="store",
                      dest="dbname",
                      help="Database where information is stored")
    parser.add_option("-u", "--db-user",
                      action="store",
                      dest="dbuser",
                      default="root",
                      help="Database user")
    parser.add_option("-p", "--db-password",
                      action="store",
                      dest="dbpassword",
                      default="",
                      help="Database password")
    parser.add_option("-g", "--debug",
                      action="store_true",
                      dest="debug",
                      default=False,
                      help="Debug mode")
    parser.add_option("-t", "--token",
                      action="store",
                      dest="token",
                      help="Slack access token")
    parser.add_option("-a", "--all",
                      action="store_true",
                      dest="all_channels",
                      help="Download all Slack channels including archived.")


    (opts, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("Wrong number of arguments")
    if not opts.logformat:
        parser.error("--format is needed")

    if opts.logformat != 'slack':
        if not(opts.data_dir and opts.dbname and opts.dbuser and opts.channel):
            parser.error("--dir --database --db-user and --channel are needed")
    else:
        if not (opts.token and opts.dbname and opts.dbuser):
            print opts
            parser.error("--database --db-user and --token are needed")

    return opts


DATE_FILENAME_REGEXP = re.compile(r'^(\d{4}\d{2}\d{2})(\.(.*))?$')
CHANNEL_FILENAME_REGEXP = re.compile(r'^#(.+)[\.-](\d{4}-\d{2}-\d{2})(\.(.*))?$')

def parse_irc_filename(filename):
    """Test file name"""
    m = CHANNEL_FILENAME_REGEXP.match(filename)
    if m:
        return string_to_datetime(m.group(2), "%Y-%m-%d")

    m = DATE_FILENAME_REGEXP.match(filename)
    if m:
        return string_to_datetime(m.group(1), "%Y%m%d")
    raise Error("File name does not contain a valid date: %s" % filename)


def get_slack_users(token):
    url_slack =  "https://slack.com/api/"
    logging.info("Getting users list ... ")
    url_users = url_slack + "users.list?token="+ token
    logging.info(url_users)
    req = requests.get(url_users, verify=False)
    slack_users = req.json()
    return slack_users['members']

def get_slack_user(user, users):
    found = user
    for usr in users:
        if usr['id'] == user:
            found = usr['name']
            break
    return found

def parse_irc_slack(db, token, slack_users, all_channels = False):
    global count_msg, count_special_msg, count_msg_drop;

    max_messages = 1000 # 1000 max for slack api

    last_date = db.get_last_date_global()
    if last_date is not None:
        last_ts = calendar.timegm(last_date.timetuple())
        # Added 1s to avoid reinserting last message
        # In MySQL we don't have <1s resolution as in Slack API
        last_ts += 1

    url_slack =  "https://slack.com/api/"
    logging.info("Getting users list ... ")
    url_users = url_slack + "users.list?token="+ token
    logging.info(url_users)
    req = requests.get(url_users, verify=False)
    users = req.json()['members']
    for user in users:
        import pprint
        pprint.pprint(user)
        nick = user['name']
        email = None
        if 'email' in user['profile']:
            email = user['profile']['email']
        name = None
        if 'real_name' in user:
            name = user['real_name']
        db.insert_user(nick, name, email)
    logging.info("Total users: %i" % len(users))

    logging.info("Getting channel list ... ")
    url_channels = url_slack + "channels.list?token="+ token
    logging.info(url_channels)

    req = requests.get(url_channels, verify=False)
    channels = req.json()
    for chan in channels['channels']:
        archived = chan['is_archived']
        public = True # all channels from web API are public
        if not all_channels and archived:
            # Only channels not archived are stored by default
            logging.info("NOT Getting messages for archived "+ chan['name'])
            continue
        logging.info("Getting messages for "+ chan['name'])
        channel_id = db.get_channel_id(chan['name'], public, archived)
        url_msgs = url_slack + "channels.history?token="+token
        url_msgs += "&channel="+chan['id']
        url_msgs += "&count="+str(max_messages)
        if last_date is not None:
            # Incremental mode
            url_msgs += "&oldest="+str(last_ts)

        has_more_messages = True
        oldest_messages_date = None
        while has_more_messages:
            url_msgs_more = url_msgs
            if oldest_messages_date is not None:
                # Has more iteration
                url_msgs_more += "&latest="+str(oldest_messages_date)
            logging.info(url_msgs_more)
            messages = requests.get(url_msgs_more, verify=False).json()
            if 'messages' not in messages:
                logging.warn("No new messages after %s" % str(last_date))
                has_more_messages = False
                continue

            has_more_messages = messages['has_more']

            for msg in messages['messages']:

                msg_date = datetime.utcfromtimestamp(float(msg['ts']))
                # Detect the oldest message for this iteration
                if oldest_messages_date is None:
                    oldest_messages_date = float(msg['ts'])
                if float(msg['ts']) <= oldest_messages_date:
                    oldest_messages_date = float(msg['ts'])

                if 'subtype' in msg:
                    # Not a simple message: channel_join, channel_topic
                    count_special_msg += 1
                else:
                    count_msg += 1

                subtype = ''
                if 'subtype' in msg: subtype = msg['subtype']
                else: subtype = 'COMMENT'
                user = ''
                if 'user' in msg: user = get_slack_user(msg['user'], slack_users)

                try:
                    # Convert to Unicode to support unicode values
                    msg = unicode((msg['text'])).encode('utf-8')
                    db.insert_message(msg_date, user, msg, subtype , channel_id)
                except UnicodeEncodeError:
                    logging.error("Can't insert message " + msg['text'])
                    count_msg_drop += 1


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
    last_date = db.get_last_date(channel_id)

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

            db.insert_message(date, nick, text, what.value, channel_id)
            count_msg_new += 1
    except Exception as e:
        raise Error("Error parsing %s file: %s" % (filepath, e))
    finally:
        infile.close()
    return count_msg, count_msg_new


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')

    opts = read_options()

    db = Database(opts.dbuser, opts.dbpassword, opts.dbname)
    db.open_database()
    db.create_tables()
    count_msg = count_msg_new = count_msg_drop = count_files_drop = 0
    count_special_msg = 0

    if opts.logformat in ['plain','html']:
        channel_id = db.get_channel_id(opts.channel)
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
    elif opts.logformat in ['slack']:
        logging.info("Slack analysis")
        slack_users = get_slack_users(opts.token)
        parse_irc_slack(db, opts.token, slack_users, opts.all_channels)

    db.close_database()
    print("Total messages: %s" % (count_msg))
    print("Total special messages: %s" % (count_special_msg))
    print("Total new messages: %s" % (count_msg_new))
    print("Total drop messages: %s" % (count_msg_drop))
    print("Total log files drop: %s" % (count_files_drop))
    sys.exit(0)
