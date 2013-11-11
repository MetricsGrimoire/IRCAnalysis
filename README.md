IRCAnalysis
===========

IRC Analysis Tool

Usage example:

    acs@lenovix:~/devel/IRCAnalysis$ mysqladmin -u root create ircdb
    acs@lenovix:~/devel/IRCAnalysis$ ./irc_analysis.py -d ircdb --channel test --format plain --dir=test/data/
    ...
    Total messages: 5552
 
A table irclog is created in the "ircdb" with all the information parsed from irc channel.

    mysql> select count(*) from irclog;
    +----------+
    | count(*) |
    +----------+
    |     5552 |
    +----------+
