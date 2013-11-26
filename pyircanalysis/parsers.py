# -*- coding: utf-8 -*-
#
# IRC Parser module
# 
# Copyright (C) 2012-2013 Bitergia
# Copyright (c) 2005-2013, Marius Gedminas 
# Copyright (c) 2000, Jeffrey W. Waugh
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
#   Santiago Dueñas <sduenas@bitergia.com>
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#
# Original authors:
#   Marius Gedminas <marius@pov.lt> (irclog2html Python port)
#   Jeff Waugh <jdub@perkypants.org> (irclog2html original author)
#
# Note: Most of the source code of PlainIRCParser was taken from Marius Gedminas'
#   irclog2html.py tool, released under the terms of the GNU GPL.
#   See http://mg.pov.lt/irclog2html/ for more information.
#   Thanks to the author for this great tool
#

import re
import dateutil.parser

from bs4 import BeautifulSoup


class Enum(object):
    """Enumerated value."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


class LogParser(object):
    """Abstract class for parsing IRC logs.

    Derived class must implement __iter__ method.
    When iterated, can yields one of the following events:

    time, COMMENT, (nick, text)
    time, ACTION, text
    time, JOIN, text
    time, PART, text,
    time, NICKCHANGE, (text, oldnick, newnick)
    time, SERVER, text

    Text is a pure ASCII or Unicode string.
    """
    # List of actions
    COMMENT = Enum('COMMENT')
    ACTION = Enum('ACTION')
    JOIN = Enum('JOIN')
    PART = Enum('PART')
    NICKCHANGE = Enum('NICKCHANGE')
    SERVER = Enum('SERVER')
    OTHER = Enum('OTHER')

    def __init__(self, infile, dircproxy=False):
        self.infile = infile
        self.dircproxy = dircproxy

    def decode(self, s):
        """Convert 8-bit string to Unicode.

        Supports xchat's hybrid Latin/Unicode encoding, as documented here:
        http://xchat.org/encoding/
        """
        if isinstance(s, unicode):
            # Accept input that's already Unicode, for convenience
            return s
        try:
            return s.decode('UTF-8')
        except UnicodeError:
            return s.decode('cp1252', 'replace')

    def __iter__(self):
        raise NotImplementedError()


class PlainLogParser(LogParser):
    """Parse a plain text IRC log file.

    When iterated, yields the following events:

    time, COMMENT, (nick, text)
    time, ACTION, text
    time, JOIN, text
    time, PART, text,
    time, NICKCHANGE, (text, oldnick, newnick)
    time, SERVER, text

    Text is a pure ASCII.

    TODO: activate Unicode support.
    """
    TIME_REGEXP = re.compile(
            r'^\[?(' # Optional [
            r'(?:\d{4}-\d{2}-\d{2}T|\d{2}-\w{3}-\d{4} |\w{3} \d{2} |\d{2} \w{3} )?' # Optional date
            r'\d\d:\d\d(:\d\d)?' # Mandatory HH:MM, optional :SS
            r')\]? +') # Optional ], mandatory space
    NICK_REGEXP = re.compile(r'^<(.*?)(!.*)?>\s')
    DIRCPROXY_NICK_REGEXP = re.compile(r'^<(.*?)(!.*)?>\s[\+-]?')
    JOIN_REGEXP = re.compile(r'^(?:\*\*\*|-->)\s.*joined')
    PART_REGEXP = re.compile(r'^(?:\*\*\*|<--)\s.*(quit|left)')
    SERVMSG_REGEXP = re.compile(r'^(?:\*\*\*|---)\s')
    NICK_CHANGE_REGEXP = re.compile(
            r'^(?:\*\*\*|---)\s+(.*?) (?:are|is) now known as (.*)')

    def __init__(self, infile, dircproxy=False):
        LogParser.__init__(self, infile, dircproxy)

        if self.dircproxy:
            self.NICK_REGEXP = self.DIRCPROXY_NICK_REGEXP

    def __iter__(self):
        for line in self.infile:
            # FIXME: activate UTF-8 decoding
            # line = self.decode(line).rstrip('\r\n')
            line = line.encode('utf-8').rstrip('\r\n')
            if not line:
                continue

            m = self.TIME_REGEXP.match(line)
            if m:
                time = dateutil.parser.parse(m.group(1))
                line = line[len(m.group(0)):]
            else:
                time = None

            m = self.NICK_REGEXP.match(line)
            if m:
                nick = m.group(1)
                text = line[len(m.group(0)):]
                yield time, self.COMMENT, (nick, text)
            elif line.startswith('* ') or line.startswith('*\t'):
                yield time, self.ACTION, line
            elif self.JOIN_REGEXP.match(line):
                yield time, self.JOIN, line
            elif self.PART_REGEXP.match(line):
                yield time, self.PART, line
            else:
                m = self.NICK_CHANGE_REGEXP.match(line)
                if m:
                    oldnick = m.group(1)
                    newnick = m.group(2)
                    line = line
                    yield time, self.NICKCHANGE, (line, oldnick, newnick)
                elif self.SERVMSG_REGEXP.match(line):
                    yield time, self.SERVER, line
                else:
                    yield time, self.OTHER, line


class HTMLLogParser(LogParser):
    """Parse a HTML IRC log file.

    When iterated, yields the following events:

    time, COMMENT, (nick, text)
    time, ACTION, text
    time, JOIN, text
    time, PART, text,
    time, SERVER, text

    Text is a pure ASCII.

    TODO: activate Unicode support.
    """
    TIME_REGEXP = re.compile(
            r'^\[?(' # Optional [
            r'(?:\d{4}-\d{2}-\d{2}T|\d{4}/\d{2}/\d{2} |\d{2}-\w{3}-\d{4} |\w{3} \d{2} |\d{2} \w{3} )?' # Optional date
            r'\d\d:\d\d(:\d\d)?' # Mandatory HH:MM, optional :SS
            r')\]? +') # Optional ], mandatory space
    NICK_REGEXP = re.compile(r'^<(.*?)(!.*)?>\s')
    DIRCPROXY_NICK_REGEXP = re.compile(r'^<(.*?)(!.*)?>\s[\+-]?')
    JOIN_REGEXP = re.compile(r'^(?:@)\s.*joined')
    PART_REGEXP = re.compile(r'^(?:@)\s.*(Quit|left)')
    SERVMSG_REGEXP = re.compile(r'^(?:@)\s')

    def __init__(self, infile, dircproxy=False):
        LogParser.__init__(self, infile, dircproxy)

        if self.dircproxy:
            self.NICK_REGEXP = self.DIRCPROXY_NICK_REGEXP

    def _read_lines(self):
        html = self.infile.read()
        bs = BeautifulSoup(html)
        lines = [line.text
                for line in bs.find('table', attrs={'class': 'irclog'}).find_all('td')]
        return lines

    def __iter__(self):
        self.lines = self._read_lines()

        for line in self.lines:
            line = line.encode('utf-8')

            if not line:
                continue

            m = self.TIME_REGEXP.match(line)
            if m:
                time = dateutil.parser.parse(m.group(1))
                line = line[len(m.group(0)):]
            else:
                time = None

            m = self.NICK_REGEXP.match(line)
            if m:
                nick = m.group(1)
                text = line[len(m.group(0)):]
                yield time, self.COMMENT, (nick, text)
            elif line.startswith('* ') or line.startswith('*\t'):
                yield time, self.ACTION, line
            elif self.JOIN_REGEXP.match(line):
                yield time, self.JOIN, line
            elif self.PART_REGEXP.match(line):
                yield time, self.PART, line
            elif self.SERVMSG_REGEXP.match(line):
                yield time, self.SERVER, line
            else:
                yield time, self.OTHER, line
