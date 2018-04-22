=========
CHANGELOG
=========

Apr 22, 2018
------------
- Added notification invalid token in retrieval of message to catch apparently valid tokens that are not

Apr 21, 2018
------------
- Rebranded from Spark to Cisco Webex Teams
- Improved visuals on welcome page
- Added disabling of notifications when app is in /disable

Feb 7, 2018
------------
- Add /team link team_name to link team_name to the always current members of the room

Jan 30, 2018
------------
- Add support for /topofmind reminder on HH:MM to explicitly set the UTC time for the reminder
- Add new /todo command with aliases /followup and /fu with reminder support
- Add support for hidden /me full command

Jan 16, 2018
------------
- Full update to support new actingweb 2.3.0 API
- Many smaller tweaks to texts and responses to improve user experience
- Renaming /myurl to /me and update with more info, both from Army Knife account and from Cisco Webex Teams account
- Automatically print out new top of mind list after a change
- Cleaned up messaging to always use bot as sender unless there is a need to send a message into a non-bot room
- Added a series of tests to as early as possible drop messages that should not be processed
- Added support for more than 100 members in /listroom, /copyroom, and /team commands
- Fixed bug in /cleanwebhooks command that disabled the bot


Dec 16, 2017
------------

- Lots of changes, ready for production?

Nov 29, 2017
-----------

- Forked from actingwebdemo app for aws


