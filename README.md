IRCAnalysis
===========

IRC Analysis Tool

Usage example:

* Download Sample data: wget http://bots.wmflabs.org/~wm-bot/logs/%23wikimedia-fundraising/%23wikimedia-fundraising.tar.gz
* Process it:
    acs@lenovix:~/devel/IRCAnalysis$ mkdir data
    acs@lenovix:~/devel/IRCAnalysis$ cd data/
    acs@lenovix:~/devel/IRCAnalysis/data$ tar xfz ../#wikimedia-fundraising.tar.gz 
    acs@lenovix:~/devel/IRCAnalysis/data$ cd ..
    acs@lenovix:~/devel/IRCAnalysis$ mysqladmin -u root create ircdb
    acs@lenovix:~/devel/IRCAnalysis$ ./irc-analysis.py -d ircdb --dir=data/
    ...
    Total messages: 5552
 
A table irclog is created in the "ircdb" with all the information parsed from irc channel.

    mysql> select count(*) from irclog;
    +----------+
    | count(*) |
    +----------+
    |     5552 |
    +----------+