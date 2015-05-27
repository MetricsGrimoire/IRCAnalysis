# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2015 Bitergia
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

import sys
import unittest

if not '..' in sys.path:
    sys.path.insert(0, '..')

from pyircanalysis.parsers import LogParser
from irc_analysis import Error, parse_irc_filename, string_to_datetime, parse_irc_file


MEDIAWIKI_LOG_PATH = 'data/mediawiki_log'


class MockDBConfig(object):

    def __init__(self, user='root', password='', database='mock_db_irc_test'):
        self.user = user
        self.password = password
        self.database = database


class MockIRCDB(object):

    def __init__(self, config):
        """Mock database for testing purposes"""
        import MySQLdb

        self.config = config
        # This is the database object used by the parser
        self.db = None

        # Private connection for executing create, delete,
        # and drop queries
        self._conn = MySQLdb.connect(user=self.config.user,
                                     passwd=self.config.password)

    def setup(self):
        """Setup a database for testing"""
        from pyircanalysis.database import Database

        cursor = self._conn.cursor()
        query = 'CREATE DATABASE ' + self.config.database
        query = query + ' CHARACTER SET utf8 COLLATE utf8_unicode_ci'
        cursor.execute(query)
        cursor.close()

        # This is the database object used by the parser
        self.db = Database(self.config.user, self.config.password,
                           self.config.database)
        self.db.open_database()
        self.db.create_tables()

    def teardown(self):
        """Database teardown"""
        self.db.close_database()
        cursor = self._conn.cursor()
        query = 'DROP DATABASE ' + self.config.database
        cursor.execute(query)
        cursor.close()
        self._conn.close()

    def clean(self):
        """Clean database"""
        cursor = self._conn.cursor()
        query = 'DELETE FROM ' + self.config.database + '.irclog'
        cursor.execute(query)
        query = 'DELETE FROM ' + self.config.database + '.channels'
        cursor.execute(query)
        query = 'DELETE FROM ' + self.config.database + '.people'
        cursor.execute(query)
        cursor.close()

    def count_num_messages(self, channel_id=None):
        """Count the number of messages inserted in the database

        :param channel_id: id of the channel
        :type channel_id: str

        :return: dict storing the number of entries per action type
        """
        query = 'SELECT type, COUNT(id) FROM irclog'
        if channel_id:
            query = query + ' WHERE channel_id = %s'
        query = query + ' GROUP BY type'

        cursor = self.db.cursor
        cursor.execute(query, (channel_id))
        results = cursor.fetchall()
        actions = {row[0] : row[1] for row in results}
        return actions

    def count_num_people(self):
        """Count the number of people inserted in the database

        :return: number of people
        """
        query = 'SELECT COUNT(*) FROM people'

        cursor = self.db.cursor
        cursor.execute(query)
        results = cursor.fetchone()
        npeople = results[0]
        return npeople


class TestIRCAnalysisMiscFunctions(unittest.TestCase):

    def test_string_to_datetime(self):
        """Test conversion of possible dates in string to datetime format"""
        from datetime import datetime

        dt = string_to_datetime('2013-10-15', '%Y-%m-%d')
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 15)

        dt = string_to_datetime('20130608', '%Y%m%d')
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 8)

        self.assertRaises(Error, string_to_datetime, '2012-13-32', '%Y-%m-%d')
        self.assertRaises(Error, string_to_datetime, 'xyzzy', '%Y%m%d')

    def test_parse_irc_filename(self):
        """Test possible file name patterns"""

        dt = parse_irc_filename('20130517.log')
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 17)

        dt = parse_irc_filename('20130517')
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 17)

        dt = parse_irc_filename('#channel-2013-05-17.txt')
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 17)

        dt = parse_irc_filename('#channel.2013-05-17.log')
        self.assertEqual(dt.year, 2013)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 17)

        self.assertRaises(Error, parse_irc_filename, '#channel-2013.log')
        self.assertRaises(Error, parse_irc_filename, '2013.log')
        self.assertRaises(Error, parse_irc_filename, '20131310.log')
        self.assertRaises(Error, parse_irc_filename, '#2013-13-10.log')

class TestParseIRCFile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = MockDBConfig()
        cls.mock_db = MockIRCDB(cls.config)
        cls.mock_db.setup()

    @classmethod
    def tearDownClass(cls):
        cls.mock_db.teardown()

    def setUp(self):
        self.mock_db.clean()

    def test_parse_plain_text_logfile(self):
        """Parse a plain text log"""

        ch1 = self.mock_db.db.get_channel_id('ch1')
        nmsg, nmsg_new = parse_irc_file('data/#mediawiki-20010101.log', ch1,
                                        'plain', self.mock_db.db)
        actions = self.mock_db.count_num_messages(ch1)
        self.assertEqual(nmsg, 79)
        self.assertEqual(nmsg_new, 79)
        self.assertEqual(len(actions.keys()), 2)
        self.assertEqual(actions[str(LogParser.COMMENT)], 75)
        self.assertEqual(actions[str(LogParser.ACTION)], 4)

    def test_parse_text_html_logfile(self):
        """Parse a text html log"""

        ch1 = self.mock_db.db.get_channel_id('ch1')
        nmsg, nmsg_new = parse_irc_file('data/#texthtml-20071217.log', ch1,
                                        'html', self.mock_db.db)
        actions = self.mock_db.count_num_messages(ch1)
        self.assertEqual(nmsg, 173)
        self.assertEqual(nmsg_new, 173)
        self.assertEqual(len(actions.keys()), 5)
        self.assertEqual(actions[str(LogParser.COMMENT)], 59)
        self.assertEqual(actions[str(LogParser.JOIN)], 62)
        self.assertEqual(actions[str(LogParser.PART)], 47)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 2)
        self.assertEqual(actions[str(LogParser.SERVER)], 3)

    def test_parse_table_html_logfile(self):
        """Parse a table html log"""

        ch1 = self.mock_db.db.get_channel_id('ch1')
        nmsg, nmsg_new = parse_irc_file('data/#tablehtml-20131211.log', ch1,
                                        'html', self.mock_db.db)
        self.assertEqual(nmsg, 153)
        self.assertEqual(nmsg_new, 153)
        actions = self.mock_db.count_num_messages()
        self.assertEqual(len(actions.keys()), 4)
        self.assertEqual(actions[str(LogParser.COMMENT)], 39)
        self.assertEqual(actions[str(LogParser.JOIN)], 43)
        self.assertEqual(actions[str(LogParser.PART)], 68)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 3)

    def test_override_log_date(self):
        """Override the date of the filename

        If the date is overridden, new messages will be inserted although
        the two logs have the same date in their filename or stored
        in log messages.
        """
        force_date = string_to_datetime('2008-01-01', '%Y-%m-%d')

        ch1 = self.mock_db.db.get_channel_id('ch1')
        parse_irc_file('data/#texthtml-20071217.log', ch1, 'html',
                       self.mock_db.db)
        parse_irc_file('data/#texthtml-20071217.log', ch1, 'html',
                       self.mock_db.db, force_date)

        actions = self.mock_db.count_num_messages()
        self.assertEqual(len(actions.keys()), 5)
        self.assertEqual(actions[str(LogParser.COMMENT)], 118)
        self.assertEqual(actions[str(LogParser.JOIN)], 124)
        self.assertEqual(actions[str(LogParser.PART)], 94)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 4)
        self.assertEqual(actions[str(LogParser.SERVER)], 6)

    def test_parse_log_from_distinct_channels(self):
        """Parse files from distinct channels"""

        ch1 = self.mock_db.db.get_channel_id('ch1')
        nmsg, nmsg_new = parse_irc_file('data/#mediawiki-20010101.log', ch1,
                                        'plain', self.mock_db.db)
        actions = self.mock_db.count_num_messages(ch1)
        self.assertEqual(nmsg, 79)
        self.assertEqual(nmsg_new, 79)
        self.assertEqual(len(actions.keys()), 2)
        self.assertEqual(actions[str(LogParser.COMMENT)], 75)
        self.assertEqual(actions[str(LogParser.ACTION)], 4)

        ch2 = self.mock_db.db.get_channel_id('ch2')
        nmsg, nmsg_new = parse_irc_file('data/#ceph.20010101.log', ch2,
                                        'plain', self.mock_db.db)
        actions = self.mock_db.count_num_messages(ch2)
        self.assertEqual(nmsg, 95)
        self.assertEqual(nmsg_new, 95)
        self.assertEqual(len(actions.keys()), 4)
        self.assertEqual(actions[str(LogParser.COMMENT)], 49)
        self.assertEqual(actions[str(LogParser.JOIN)], 22)
        self.assertEqual(actions[str(LogParser.PART)], 21)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 3)

        # Check the total count of messages by type
        actions = self.mock_db.count_num_messages()
        self.assertEqual(len(actions.keys()), 5)
        self.assertEqual(actions[str(LogParser.COMMENT)], 124)
        self.assertEqual(actions[str(LogParser.ACTION)], 4)
        self.assertEqual(actions[str(LogParser.JOIN)], 22)
        self.assertEqual(actions[str(LogParser.PART)], 21)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 3)

    def test_parse_log_from_same_channel(self):
        """Parse files from the same channel"""

        ch1 = self.mock_db.db.get_channel_id('ch1')
        parse_irc_file('data/#texthtml-20071217.log', ch1, 'html',
                       self.mock_db.db)
        parse_irc_file('data/#tablehtml-20131211.log', ch1, 'html',
                       self.mock_db.db)

        actions = self.mock_db.count_num_messages()
        self.assertEqual(len(actions.keys()), 5)
        self.assertEqual(actions[str(LogParser.COMMENT)], 98)
        self.assertEqual(actions[str(LogParser.JOIN)], 105)
        self.assertEqual(actions[str(LogParser.PART)], 115)
        self.assertEqual(actions[str(LogParser.NICKCHANGE)], 5)
        self.assertEqual(actions[str(LogParser.SERVER)], 3)


class TestParseIRCLog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = MockDBConfig()
        cls.mock_db = MockIRCDB(cls.config)
        cls.mock_db.setup()

    @classmethod
    def tearDownClass(cls):
        cls.mock_db.teardown()

    def setUp(self):
        self.mock_db.clean()

    def test_mediawiki_log(self):
        """Parse MediaWiki log files"""
        import os

        ch = self.mock_db.db.get_channel_id('mediawiki')

        files = os.listdir(MEDIAWIKI_LOG_PATH)
        files.sort()

        for logfile in files:
            date = parse_irc_filename(logfile)
            filepath = os.path.join(MEDIAWIKI_LOG_PATH, logfile)
            parse_irc_file(filepath, ch, 'plain', self.mock_db.db, date)

        actions = self.mock_db.count_num_messages()
        self.assertEqual(len(actions.keys()), 2)
        self.assertEqual(actions[str(LogParser.COMMENT)], 5443)
        self.assertEqual(actions[str(LogParser.ACTION)], 109)

        self.mock_db.db.fill_people_table()
        npeople = self.mock_db.count_num_people()
        self.assertEqual(npeople, 46)


if __name__ == '__main__':
    unittest.main(buffer=True)
