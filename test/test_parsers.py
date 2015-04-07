# -*- coding: utf-8 -*-
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

import sys
import unittest

if not '..' in sys.path:
    sys.path.insert(0, '..')

from pyircanalysis.parsers import LogParser, PlainLogParser, HTMLLogParser


def parse_plain_text_line(line):
    """Helper function for testing plain text lines.

    Parse line and print the results to the stdout.

    :param line: plain text line
    :type line: str

    :return: time, what, info
    """
    for time, what, info in PlainLogParser([line]):
        return time, what, info

def parse_log(filepath, log_type):
    """Helper function for parsing a plain file.

    :param filepath: path to the file
    :type filepath: str
    :param log_type: type of the file
    :type log_type: str (plain, html)

    :return: dict storing the number of entries per action type
    """
    import io
    infile = io.open(filepath, 'rt')

    if log_type == 'plain':
        parser = PlainLogParser(infile)
    elif log_type == 'html':
        parser = HTMLLogParser(infile)
    else:
        raise Exception("Invalid log type. Valid values are 'plain' or 'html'")

    actions = {}
    for time, what, info in parser:
        if what in actions:
            actions[what] = actions[what] + 1
        else:
            actions[what] = 1
    return actions


class TestPlainLogParser(unittest.TestCase):

    def test_empty_lines(self):
        """Ignore empty lines"""

        self.assertEqual(parse_plain_text_line(''), None)
        self.assertEqual(parse_plain_text_line('\n'), None)
        self.assertEqual(parse_plain_text_line('\r\n'), None)

    def test_strip_lines(self):
        """Newline characters are stripped from the line, if they are present"""

        info = parse_plain_text_line('14:18 * mg says Hello\n')[2]
        self.assertEqual(info, '* mg says Hello')

        info = parse_plain_text_line('14:18 * mg says Hello\r\n')[2]
        self.assertEqual(info, '* mg says Hello')

        info = parse_plain_text_line('14:18 * mg says Hello\r')[2]
        self.assertEqual(info, '* mg says Hello')

    def test_timestamp_format(self):
        """Test several timestamp formats"""

        ts = parse_plain_text_line('14:18 <mg> Hello!')[0]
        self.assertEqual(ts.hour, 14)
        self.assertEqual(ts.minute, 18)

        ts = parse_plain_text_line('[14:18] <mg> Hello!')[0]
        self.assertEqual(ts.hour, 14)
        self.assertEqual(ts.minute, 18)

        ts = parse_plain_text_line('[14:18:55] <mg> Hello!')[0]
        self.assertEqual(ts.hour, 14)
        self.assertEqual(ts.minute, 18)
        self.assertEqual(ts.second, 55)

        ts = parse_plain_text_line('[2004-02-04T14:18:55] <mg> Hello!')[0]
        self.assertEqual(ts.year, 2004)
        self.assertEqual(ts.month, 2)
        self.assertEqual(ts.day, 4)
        self.assertEqual(ts.hour, 14)
        self.assertEqual(ts.minute, 18)
        self.assertEqual(ts.second, 55)

        ts = parse_plain_text_line('[02-Feb-2004 14:18:55] <mg> Hello!')[0]
        self.assertEqual(ts.year, 2004)
        self.assertEqual(ts.month, 2)
        self.assertEqual(ts.day, 2)
        self.assertEqual(ts.hour, 14)
        self.assertEqual(ts.minute, 18)
        self.assertEqual(ts.second, 55)

        ts = parse_plain_text_line('[15 Jan 08:42] <mg> +++Hello+++')[0]
        self.assertEqual(ts.month, 1)
        self.assertEqual(ts.day, 15)
        self.assertEqual(ts.hour, 8)
        self.assertEqual(ts.minute, 42)
        self.assertEqual(ts.second, 0)

    def test_no_timestamp(self):
        """If there is no timestamp on the line, the parser returns None"""

        ts = parse_plain_text_line('* mg says Hello')[0]
        self.assertEqual(ts, None)

    def test_comment_line(self):
        """Test COMMENT"""

        ts, what, info = parse_plain_text_line('<nick> text')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.COMMENT)
        self.assertEqual(info[0], 'nick')
        self.assertEqual(info[1], 'text')

        ts, what, info = parse_plain_text_line('<nick&gt; text&gt; ->')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.COMMENT)
        self.assertEqual(info[0], 'nick')
        self.assertEqual(info[1], 'text&gt; ->')

    def test_action_line(self):
        """Test ACTIONS"""

        ts, what, info = parse_plain_text_line('* nick text')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.ACTION)
        self.assertEqual(info, '* nick text')

        ts, what, info = parse_plain_text_line('*\tnick text')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.ACTION)
        self.assertEqual(info, '*\tnick text')

    def test_join_line(self):
        """Test JOIN"""

        ts, what, info = parse_plain_text_line('*** someone joined #channel')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.JOIN)
        self.assertEqual(info, '*** someone joined #channel')

        ts, what, info = parse_plain_text_line('--> someone joined')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.JOIN)
        self.assertEqual(info, '--> someone joined')

    def test_part_line(self):
        """Test PART"""

        ts, what, info = parse_plain_text_line('*** someone quit')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.PART)
        self.assertEqual(info, '*** someone quit')

        ts, what, info = parse_plain_text_line('<-- someone left #channel')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.PART)
        self.assertEqual(info, '<-- someone left #channel')

    def test_nickchange_line(self):
        """Test NICKCHANGE"""

        ts, what, info = parse_plain_text_line('*** X is now known as Y')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.NICKCHANGE)
        self.assertEqual(info[0], '*** X is now known as Y')
        self.assertEqual(info[1], 'X')
        self.assertEqual(info[2], 'Y')

        ts, what, info = parse_plain_text_line('--- X are now known as Y')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.NICKCHANGE)
        self.assertEqual(info[0], '--- X are now known as Y')
        self.assertEqual(info[1], 'X')
        self.assertEqual(info[2], 'Y')

    def test_server_line(self):
        """Test SERVER"""

        ts, what, info = parse_plain_text_line('--- welcome to irc.example.org')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.SERVER)
        self.assertEqual(info, '--- welcome to irc.example.org')

        ts, what, info = parse_plain_text_line('*** welcome to irc.example.org')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.SERVER)
        self.assertEqual(info, '*** welcome to irc.example.org')

    def test_other_line(self):
        """All unrecognized lines are reported as OTHER"""

        ts, what, info = parse_plain_text_line('what is this line doing in my IRC log file?')
        self.assertEqual(ts, None)
        self.assertEqual(what, LogParser.OTHER)
        self.assertEqual(info, 'what is this line doing in my IRC log file?')

    def test_parse_log_file(self):
        """Parse log files"""

        actions = parse_log('data/plain_mediawiki.log', 'plain')
        self.assertEqual(len(actions.keys()), 2)
        self.assertEqual(actions[LogParser.COMMENT], 75)
        self.assertEqual(actions[LogParser.ACTION], 4)

        actions = parse_log('data/plain_ceph.log', 'plain')
        self.assertEqual(len(actions.keys()), 4)
        self.assertEqual(actions[LogParser.COMMENT], 49)
        self.assertEqual(actions[LogParser.JOIN], 22)
        self.assertEqual(actions[LogParser.PART], 21)
        self.assertEqual(actions[LogParser.NICKCHANGE], 3)


class TestHTMLLogParser(unittest.TestCase):

    def test_text_html_parser(self):
        """Parse html log in text format"""

        actions = parse_log('data/text_html.log', 'html')
        self.assertEqual(len(actions.keys()), 5)
        self.assertEqual(actions[LogParser.COMMENT], 59)
        self.assertEqual(actions[LogParser.JOIN], 62)
        self.assertEqual(actions[LogParser.PART], 47)
        self.assertEqual(actions[LogParser.NICKCHANGE], 2)
        self.assertEqual(actions[LogParser.SERVER], 3)

    def test_table_html_parser(self):
        """Parse html log in table format"""

        actions = parse_log('data/table_html.log', 'html')
        self.assertEqual(len(actions.keys()), 4)
        self.assertEqual(actions[LogParser.COMMENT], 39)
        self.assertEqual(actions[LogParser.JOIN], 43)
        self.assertEqual(actions[LogParser.PART], 68)
        self.assertEqual(actions[LogParser.NICKCHANGE], 3)

    def test_parse_text_file(self):
        """Parse a plain text file"""

        actions = parse_log('data/plain_mediawiki.log', 'html')
        self.assertEqual(len(actions.keys()), 0)


if __name__ == '__main__':
    unittest.main()
