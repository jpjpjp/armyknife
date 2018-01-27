import json
import datetime
import logging
import requests
import hashlib
from actingweb import actor


class SparkBotHandler:
    """ Class with all methods to handle bot requests
    """

    def __init__(self, spark=None):
        self.spark = spark

    def init_me(self):
        if not self.spark.actor_id:
            # Use delete=True here as we haven't found an actor with the right oauthId at this
            # point, so any existing actors have issues
            self.spark.me = actor.Actor(config=self.spark.config)
            self.spark.me.create(url=self.spark.config.root, creator=self.spark.person_object,
                                 passphrase=self.spark.config.new_token(), delete=True)
        url = self.spark.config.root + self.spark.me.id
        self.spark.me.set_property('chatRoomId', self.spark.room_id)
        if not self.spark.is_actor_user:
            self.spark.link.post_message(
                self.spark.room_id,
                "**Welcome to Spark Army Knife, " + self.spark.person_object +
                "!**\n\n Please authorize the app by clicking the following link: " +
                url + "/www",
                markdown=True)
        else:
            self.spark.link.post_message(
                self.spark.room_id,
                "Welcome back!\n\nPlease re-authorize the app by clicking the following link: " +
                url + "/www?refresh=true",
                markdown=True)

    def rooms_created(self):
        if not self.spark.me.id:
            pass

    def memberships_created(self):
        if self.spark.is_bot_object:
            if self.spark.room_type == 'group':
                self.spark.link.post_bot_message(
                    spark_id=self.spark.room_id,
                    text="**Welcome to Spark Army Knife!**\n\n To use, please create a 1:1 room with " +
                         self.spark.config.bot['email'] +
                         ". If you don't get an answer, type /init in that room.",
                    markdown=True)
        else:
            # The user was added
            if self.spark.room_type == 'direct':
                self.init_me()

    def exec_all_users(self):
        if not self.spark.msg_list:
            return
        msg = self.spark.msg_data['text']
        users = actor.Actors(config=self.spark.config).fetch()
        if len(self.spark.msg_list) < 3 or self.spark.msg_list[2] == 'help':
            self.spark.link.post_admin_message(
                "**Usage of /all-users**\n\n"
                "count: Make a count of all users\n\n"
                "list: List all users\n\n"
                "countfilter/listfilter/markfilter: Make a count, list, or mark a set of users.\n\n"
                "countfilter/listfilter/markfilter can all be used with `attr` and `attr value`\n\n"
                "where no value means any users with attr set, and value = None mean attr not set.\n\n"
                "If value is supplied, only users with attr matching value will be matched."
                "When a set of users have been marked, the following commands can be used:\n\n"
                "marked-message `msg`: Send msg to all users\n\n"
                "marked-list: List all users marked\n\n"
                "marked-clear: Clear all users marked\n\n"
                "marked-delete: Delete all accounts marked \n\n", markdown=True)
            return
        cmd = self.spark.msg_list[2].lower()
        counters = {"total": 0}
        out = ""
        if 'filter' in cmd:
            if len(self.spark.msg_list) >= 4:
                msg_filter = self.spark.msg_list[3]
            else:
                self.spark.link.post_admin_message(
                    "You need to supply a filter: /all-users " + str(cmd) + " `filter value(optional)`",
                    markdown=True)
                return
        else:
            msg_filter = None
        if msg_filter and len(self.spark.msg_list) >= 5:
            filter_value = self.spark.msg_list_wcap[4]
        else:
            filter_value = None
        if cmd == "marked-message" and len(self.spark.msg_list) >= 4:
            msg_markdown = msg[
                           len(self.spark.msg_list[0]) +
                           len(self.spark.msg_list[1]) +
                           len(self.spark.msg_list[2]) + 2:]
        else:
            msg_markdown = None
        if cmd == "list":
            out += "**List of all actors**\n\n"
        elif cmd == "count":
            out += "**Count of actors**\n\n"
        elif cmd == "listfilter":
            out += "**List of actors "
        elif cmd == "countfilter":
            out += "**Count of actors "
        elif cmd == "markfilter":
            out += "**Setting mark on actors "
        elif cmd == "marked-clear":
            out += "**Clearing marks for all actors**\n\n"
        elif cmd == "marked-list":
            out += "**Listing all marked actors**\n\n"
        elif cmd == "marked-delete":
            out += "**Deleting all marked actors**\n\n"
        elif cmd == "marked-message":
            out += "**Sending message to all marked actors**\n\n"
        else:
            self.spark.link.post_admin_message(
                "Your /all-users command is not recognised. Please do just `/all-users` to get the help message.",
                markdown=True)
            return
        if 'filter' in cmd:
            if not filter_value:
                out += "with attribute " + str(msg_filter) + "**\n\n"
            elif filter_value == "None":
                out += "without attribute " + str(msg_filter) + "**\n\n"
            else:
                out += "with attribute " + str(msg_filter) + " containing " + str(filter_value) + "**\n\n"
        if len(out) > 0:
            self.spark.link.post_admin_message(out, markdown=True)
            out = ""
        for u in users:
            a = actor.Actor(actor_id=u["id"], config=self.spark.config)
            service_status = a.get_property('service_status').value
            counters["total"] += 1
            if str(service_status) in counters:
                counters[str(service_status)] += 1
            else:
                counters[str(service_status)] = 1
            if cmd == "list":
                out += "**" + a.creator + "** (" + str(a.id) + "): " + str(service_status or "None") + "\n\n"
            elif filter and ('filter' in cmd):
                attr = a.get_property(str(msg_filter)).value
                if not attr and filter_value and filter_value == "None":
                    attr = "None"
                if attr and (not filter_value or (filter_value and filter_value in attr)):
                    if str(msg_filter) in counters:
                        counters[str(msg_filter)] += 1
                    else:
                        counters[str(msg_filter)] = 1
                    if cmd == "listfilter":
                        out += "**" + a.creator + "** (" + str(a.id) + "): " + str(service_status or "None") + "\n\n"
                    elif cmd == "markfilter":
                        out += a.creator + " marked.\n\n"
                        a.set_property('filter_mark', 'true')
            elif cmd == "marked-clear":
                attr = a.get_property('filter_mark').value
                if attr and attr == 'true':
                    a.delete_property('filter_mark')
                    if 'marked-cleared' in counters:
                        counters["marked-cleared"] += 1
                    else:
                        counters["marked-cleared"] = 1
            elif cmd == "marked-list":
                attr = a.get_property('filter_mark').value
                if attr and attr == 'true':
                    out += a.creator + " (" + a.id + ")\n\n"
                    if 'marked-list' in counters:
                        counters["marked-list"] += 1
                    else:
                        counters["marked-list"] = 1
            elif cmd == "marked-message":
                attr = a.get_property('filter_mark').value
                if attr and attr == 'true':
                    no_alert = a.get_property('no_announcements').value
                    if not no_alert or no_alert != "true":
                        self.spark.link.post_bot_message(
                            email=a.get_property('email').value,
                            text=msg_markdown,
                            markdown=True)
                        if 'marked-messaged' in counters:
                            counters["marked-messaged"] += 1
                        else:
                            counters["marked-messaged"] = 1
            elif cmd == "marked-delete":
                attr = a.get_property('filter_mark').value
                if attr and attr == 'true':
                    out += a.creator + " deleted.\n\n"
                    a.delete()
                    if 'marked-deleted' in counters:
                        counters["marked-deleted"] += 1
                    else:
                        counters["marked-deleted"] = 1
            if len(out) > 3000:
                self.spark.link.post_admin_message(out, markdown=True)
                out = ""
        if len(out) > 0:
            self.spark.link.post_admin_message(out, markdown=True)
        out = "----\n\n**Grand total number of users**: " + str(counters["total"]) + "\n\n"
        del (counters["total"])
        for k, v in counters.iteritems():
            out += str(k) + ": " + str(v) + "\n\n"
        if len(out) > 0:
            self.spark.link.post_admin_message(out, markdown=True)

    def admin_commands(self):
        """ Only requests in the admin room will enter this method """

        if self.spark.cmd == "/mail":
            message = self.spark.msg_data['text'][
                      len(self.spark.msg_list_wcap[0]) +
                      len(self.spark.msg_list_wcap[1]) +
                      len(self.spark.msg_list_wcap[2]) + 3:]
            self.spark.link.post_bot_message(email=self.spark.msg_list[2], text=message)
            self.spark.link.post_admin_message("Sent the following message to " + self.spark.msg_list[2] +
                                               ":\n\n" + message,
                                               markdown=True)
        elif self.spark.cmd == "/help":
            self.spark.link.post_admin_message(
                "**Spark Army Knife: Admin Help**\n\n"
                "Use `/mail <email> message` to send somebody a message from the bot.\n\n"
                "Use `/all-users` for listing and messaging all users.",
                markdown=True)
        elif self.spark.cmd == "/all-users":
            self.exec_all_users()
        else:
            self.spark.link.post_admin_message("Unknown command. Try /help.")

    def group_commands(self):
        # Respond to @armyknife /help and @armyknife singleword
        if self.spark.cmd == '/help' or ('/' not in self.spark.cmd and len(self.spark.msg_list_wcap) <= 2):
            self.spark.link.post_bot_message(
                spark_id=self.spark.room_id,
                text="**Hi there from the Spark Army Knife!**\n\n"
                     "To use, please create a 1:1 room with the bot (" +
                     self.spark.config.bot['email'] + ").",
                markdown=True)
            if not self.spark.is_actor_user:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="**Hi there from the Spark Army Knife!**\n\n"
                         "Please type /init in the 1:1 room to authorize the app.",
                    markdown=True)

    def help(self):
        self.spark.link.post_bot_message(
            email=self.spark.person_object,
            text="**Spark Army Knife (author: Greger Wedel)**\n\n"
                 "Help message for commands that only work in the bot 1:1 room.\n\n"
                 "**App Management**\n\n"
                 "- Use `/init` to authorize the app so that all commands work.\n\n"
                 "- Use `/delete DELETENOW` to delete your Spark Army Knife account, this room, and "
                 "all data associated with this account.\n\n"
                 "- Use `/disable` to temporarily disable the Spark Army Knife account.\n\n"
                 "- Use `/enable` to enable the Spark Army Knife account.\n\n"
                 "- Use `/support <message>` to send a message to support.\n\n"
                 "- Use `/me` to get info about your Spark Army Knife account.\n\n"
                 "- Use `/recommend <email> <message>` to send a message to another user and recommend "
                 "Spark Army Knife.\n\n"
                 "- Use `/nomentionalert` to turn off 1:1 bot room alerts on mentions.\n\n"
                 "- Use `/mentionalert` to turn on (default) 1:1 bot room alerts on mentions.\n\n"
                 "- Use `/noroomalert` to turn off 1:1 bot room alerts on new rooms.\n\n"
                 "- Use `/roomalert` to turn on (default) 1:1 bot room alerts on new rooms.\n\n"
                 "- Use `/noannouncements` to turn off announcements about Spark Army Knife.\n\n"
                 "- Use `/announcements` to turn on (default) announcements about Spark Army Knife.\n\n"
                 "**Top of Mind List**\n\n"
                 "- Use `/topofmind <index> Top of mind thing ...` to list and set your top of mind "
                 "list (shortcut `/tom`).\n\n"
                 "- Use `/topofmind clear` to clear your top of mind list.\n\n"
                 "- Use `/topofmind title <Title of list>` to set the title of your top of "
                 "mind list.\n\n"
                 "- Use `/topofmind reminder on|off` to set or stop a daily reminder of your list at "
                 "this time.\n\n"
                 "**Box.com Integration**\n\n"
                 "- Use `/box <rootfolder>` to add a Box account to Spark Army Knife. "
                 "Optionally specify the folder where all Army Knife Box folders will be created.\n\n"
                 "- Use `/nobox` to disconnect and delete the Box service.\n\n"
                 "**Room management**\n\n"
                 "- Use `/countrooms` to get the number of group rooms you are a member of.\n\n"
                 "- Use `/checkmember <email|name>` to get a list of rooms that email or name is a "
                 "member of.\n\n"
                 "- Use `/deletemember <email> <room-id,room-id...>` to delete a user from a room"
                 " or list of rooms "
                 "(use Spark Id from e.g. /checkmember or /listroom).\n\n"
                 "- Use `/addmember <email> <room-id,room-id...>` to add a user to a room or"
                 " list of rooms "
                 "(use Spark Id from e.g. /checkmember or /listroom).\n\n"
                 "- Use `/manageteam add|remove|list|delete <team_name> <email(s)>` where emails"
                 " are comma-separated. "
                 "The team can also be initialized from members in a room, see /team command"
                 " below.\n\n"
                 "- Use `/manageteam list` to list all teams.\n\n"
                 "**Messaging**\n\n"
                 "- Use `/track <email> <nickname>` to track messages from a person/VIP.\n\n"
                 "- Use `/trackers` to list tracked emails.\n\n"
                 "- Use `/get <nickname>` to get a list of all messages since last time"
                 " for that person "
                 "(and `/get all` to get from all tracked people).\n\n"
                 "- Use `/untrack <email>` to stop tracking a person.\n\n"
                 "- Use `/autoreply <your_message>` to send auto-reply message to all @mentions"
                 " and direct messages "
                 "(markdown is supported).\n\n"
                 "- Use `/noautoreply` to turn off auto-reply.\n\n"
                 "- Use `/pins` to get a list of pinned messages and reminders set with /pin"
                 " command.\n\n"
                 "**Advanced Spark Commands**\n\n"
                 "- Use `/listwebhooks` to see all webhooks registered by integrations on your"
                 " account.\n\n"
                 "- Use `/deletewebhook <webhookid>` to delete a specific webhook from /listwebhooks"
                 " (**CAREFUL!!**)\n\n"
                 "- Use `/cleanwebhooks` to delete absolutely ALL webhooks registered for your"
                 " account, not only for the "
                 "Army Knife (*USE WITH CAUTION!)*\n\n",
            markdown=True)
        self.spark.link.post_bot_message(
            email=self.spark.person_object,
            text="- - -",
            markdown=True)
        self.spark.link.post_bot_message(
            email=self.spark.person_object,
            text="Help message for commands that can be used in any room:\n\n"
                 "**Top of Mind List**\n\n"
                 "- Use `@mention /topofmind` (shortcut `/tom`) to list somebody's top of mind"
                 " list.\n\n"
                 "- Use `/topofmind` (shortcut `/tom`) in a 1:1 room to list that person's top of"
                 " mind list.\n\n"
                 "- Use `/topofmind subscribe` in a 1:1 room to subscribe to that person's top of"
                 " mind list.\n\n"
                 "- Use `/topofmind unsubscribe` in a 1:1 room to unsubscribe to that person's top"
                 " of mind list.\n\n"
                 "**Room Utility Commands**\n\n"
                 "- Use `/copyroom <New Title>` to create a new room with the same members as the"
                 " one you are in.\n\n"
                 "- Use `/makepublic` to get a URL people can use to add themselves to a room. \n\n"
                 "- Use `/makeprivate` to disable this URL again and make the room private.\n\n"
                 "- Use `/listroom` to get a list of all room data for a 1:1 or group room.\n\n"
                 "- Use `/listfiles` to get a list of all files in a 1:1 or group room.\n\n"
                 "- Use `/listmembers` to get a list of all members of the current room printed in"
                 " your 1:1 Army Knife bot room."
                 " `/listmembers csv` creates a comma separated list of email addresses.\n\n"
                 "- Use: `/team init|add|remove|verify|sync <team_name>` to make a new team from"
                 " members in the room (init), and then "
                 "add, remove, or synchronize the team with a room's members. Use verify to get a"
                 " list of differences.\n\n"
                 "**Box.com Integration**\n\n"
                 "- Use `/boxfolder <foldername>` in a group room to create a new Box folder and"
                 " add all the room members "
                 "as editors to the folder. Optionally specify the name of the folder to "
                 "create (the room name is used default). \n\n"
                 "- Use `/noboxfolder` to disconnect the Box folder from the room (the folder is"
                 " not deleted on Box).\n\n"
                 "**Reminders**\n\n"
                 "- Use `/pin` or `/pin <x>` to pin the previous message in a room (or the"
                 " message x messages back). "
                 "The pinned message will be listed in your 1:1 Army Knife room.\n\n"
                 "- Use `/pin <x> +<a>[m|h|d|w]`, to create a reminder for a message some time a"
                 " into the future. "
                 "E.g. /pin 3 +2h, where m = minutes, h = hours, d = days, w = weeks\n\n"
                 "- Use `/pin 0 +<a>[m|h|d|w] <My message>` to set a reminder with no reference"
                 " to a message, e.g. `/pin 0 +2h Time to leave!`\n\n",
            markdown=True)

    def tracker_commands(self):
        if self.spark.cmd == '/track':
            if len(self.spark.msg_list) < 3:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Usage: `/track <email> <nickname>`",
                    markdown=True)
                return
            # person = spark.link.get_person()
            added = self.spark.store.add_tracker(self.spark.msg_list[1], self.spark.msg_list[2])
            if added:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Added tracking of " + self.spark.msg_list[1])
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Was not able to add tracking of " + self.spark.msg_list[1])
        elif self.spark.cmd == '/untrack':
            if self.spark.store.delete_tracker(self.spark.msg_list[1]):
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Untracked " + self.spark.msg_list[1])
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Failed untracking of " + self.spark.msg_list[1])
        elif self.spark.cmd == '/trackers':
            trackers = self.spark.store.load_trackers()
            if not trackers:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text='No people are tracked.')
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text='**Tracked users**\n\n----\n\n',
                    markdown=True)
                for tracker in trackers:
                    self.spark.link.post_bot_message(
                        email=self.spark.person_object,
                        text=tracker["email"] + ' (' + tracker["nickname"] + ')')

    def topofmind_commands(self):
        topofmind = self.spark.me.get_property('topofmind').value
        if topofmind:
            try:
                topofmind = json.loads(topofmind)
                toplist = topofmind['list']
            except (TypeError, KeyError, ValueError):
                toplist = {}
        else:
            toplist = {}
            topofmind = {'email': self.spark.me.creator, 'displayName': self.spark.me.get_property('displayName').value,
                         'title': "Top of Mind List"}
        # Handle no params
        if len(self.spark.msg_list) == 1 or (len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'help'):
            if len(toplist) == 0 or (len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'help'):
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="To set an item: `/topofmind <index> <Your top of mind item>`\n\n"
                         "Available /topofmind commands: title, clear, reminder, x delete, x insert",
                    markdown=True)
                return
            else:
                out = "**" + topofmind['title'] + "**"
                modified = self.spark.me.get_property('topofmind_modified').value
                if modified:
                    timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                    out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                out += "\n\n---\n\n"
                for i, el in sorted(toplist.items()):
                    out = out + "**" + i + "**: " + el + "\n\n"
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text=out,
                    markdown=True)
                return
        # Handle more than one param
        index = self.spark.msg_list_wcap[1]
        if index == "clear":
            self.spark.me.delete_property('topofmind')
            topofmind['list'] = {}
            out = json.dumps(topofmind)
            self.spark.me.register_diffs(target='properties', subtarget='topofmind', blob=out)
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Cleared your " + topofmind['title'])
            return
        if index == "subscriptions":
            subs = self.spark.me.get_subscriptions(target='properties', subtarget='topofmind', callback=True)
            if len(subs) > 0:
                out = "**Your Top Of Mind subscriptions on others**\n\n"
            else:
                out = ''
            for s in subs:
                out += "Subscription " + s["subscriptionid"] + " on peer " + s["peerid"] + "\n\n"
            subs = self.spark.me.get_subscriptions(target='properties', subtarget='topofmind', callback=False)
            if len(subs) > 0:
                out += "----\n\n**Others subscribing to your Top Of Mind**\n\n"
            for s in subs:
                out += "Subscription " + s["subscriptionid"] + " from peer " + s["peerid"] + "\n\n"
            if len(out) > 0:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text=out,
                    markdown=True)
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="There are no subscriptions.",
                    markdown=True)
            return
        if index == "title":
            if len(self.spark.msg_list_wcap) < 3:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Use: /topofmind title <Your new list title>")
                return
            topofmind['title'] = self.spark.msg_data['text'][
                                 len(self.spark.msg_list_wcap[0]) +
                                 len(self.spark.msg_list_wcap[1]) + 2:]
            out = json.dumps(topofmind)
            self.spark.me.set_property('topofmind', out)
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Set top of mind list title to " + topofmind['title'])
            return
        if index == "reminder":
            if len(self.spark.msg_list_wcap) != 3:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="You must use reminder on or off! (/topofmind reminder on|off)")
                return
            if self.spark.msg_list_wcap[2] == "on":
                self.spark.store.delete_pinned_messages(comment="#/TOPOFMIND")
                now = datetime.datetime.utcnow()
                targettime = now + datetime.timedelta(days=1)
                self.spark.store.save_pinned_message(comment='#/TOPOFMIND', timestamp=targettime)
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Set reminder of top of mind list at this time each day")
            elif self.spark.msg_list_wcap[2] == "off":
                self.spark.store.delete_pinned_messages(comment="#/TOPOFMIND")
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Deleted daily reminder of " + topofmind['title'])
            return
        if index:
            listitem = self.spark.msg_data['text'][
                       len(self.spark.msg_list_wcap[0]) +
                       len(self.spark.msg_list_wcap[1]) + 2:]
            now = datetime.datetime.utcnow()
            self.spark.me.set_property('topofmind_modified', now.strftime('%Y-%m-%d %H:%M'))
            if listitem == "delete":
                del (toplist[index])
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Deleted list item " + str(index))
                try:
                    if int(index) != 0:
                        newlist = {}
                        for k in toplist:
                            if int(k) < int(index):
                                newlist[k] = toplist[k]
                            else:
                                newlist[int(k) - 1] = toplist[k]
                        toplist = newlist
                except ValueError:
                    pass
            elif listitem[0:6] == "insert":
                try:
                    listitem = listitem[7:]
                    if int(index) != 0:
                        newlist = {}
                        for k in toplist:
                            if int(k) < int(index):
                                newlist[k] = toplist[k]
                            else:
                                newlist[int(k) + 1] = toplist[k]
                        newlist[index] = listitem
                        toplist = newlist
                        self.spark.link.post_bot_message(
                            email=self.spark.person_object,
                            text="**Inserted list item " + str(index) + "** with text " + listitem,
                            markdown=True)
                except ValueError:
                    self.spark.link.post_bot_message(
                        email=self.spark.person_object,
                        text="You cannot use insert command when you have list item(s) that have text as index.",
                        markdown=True)
            else:
                toplist[index] = listitem
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Added list item **" + str(index) + "** with text `" + toplist[index] + "`",
                    markdown=True)
            topofmind['list'] = toplist
            out = json.dumps(topofmind, sort_keys=True)
            self.spark.me.set_property('topofmind', out)
            self.spark.me.register_diffs(target='properties', subtarget='topofmind', blob=out)
            # List out the updated list
            toplist = json.loads(out)['list']
            out = "**" + topofmind['title'] + "**"
            modified = self.spark.me.get_property('topofmind_modified').value
            if modified:
                timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
            out += "\n\n---\n\n"
            for i, el in sorted(toplist.items()):
                out = out + "**" + str(i) + "**: " + str(el) + "\n\n"
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text=out,
                markdown=True)

    def team_commands(self):
        if len(self.spark.msg_list) < 3 and not (len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'list'):
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Usage: `/manageteam add|remove|list <teamname> <email(s)>` where emails are"
                     " comma-separated\n\n"
                     "Use `/manageteam list` to list all teams",
                markdown=True)
            return
        team_cmd = self.spark.msg_list[1]
        if len(self.spark.msg_list) == 2 and team_cmd == 'list':
            out = "**List of teams**\n\n----\n\n"
            properties = self.spark.me.get_properties()
            if properties and len(properties) > 0:
                found = False
                for name, value in properties.items():
                    if 'team-' in name:
                        try:
                            team = json.loads(value)
                        except ValueError:
                            team = value
                        found = True
                        out += "**" + name[len('team-'):] + "**: "
                        sep = ""
                        for t in team:
                            out += sep + str(t)
                            sep = ","
                        out += "\n\n"
                if not found:
                    out += "No teams\n\n"
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text=out,
                markdown=True)
            return
        team_name = self.spark.msg_list[2]
        if team_cmd != 'add' and team_cmd != 'remove' and team_cmd != 'list' and team_cmd != 'delete':
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Usage: `/manageteam add|remove|list|delete <teamname> <email(s)>` where emails"
                     " are comma-separated",
                markdown=True)
            return
        if len(self.spark.msg_list) > 3:
            emails = self.spark.msg_data['text'][len(self.spark.msg_list[0]) +
                                                 len(self.spark.msg_list[1]) +
                                                 len(self.spark.msg_list[2]) +
                                                 2:].replace(" ", "").split(',')
        else:
            emails = []
        team_str = self.spark.me.get_property('team-' + team_name).value
        if not team_str:
            team_list = []
        else:
            try:
                team_list = json.loads(team_str)
            except (TypeError, ValueError, KeyError):
                team_list = []
        out = ''
        if len(team_list) == 0 and team_cmd == 'list':
            out = "The team does not exist."
        elif team_cmd == 'list':
            out = "**Team members of team " + team_name + "**\n\n"
            for t in team_list:
                out += t + "\n\n"
        elif team_cmd == 'add':
            for e in emails:
                out += "Added " + e + "\n\n"
                team_list.append(str(e.strip()))
        elif team_cmd == 'init':
            for e in emails:
                out += "Added " + e + "\n\n"
                team_list.append(str(e))
        elif team_cmd == 'delete':
            if len(self.spark.msg_list) > 3:
                out += "Use remove to remove an email address from a team. Delete is to delete an entire team!\n\n"
            else:
                out += "Deleted team " + team_name + "\n\n"
                self.spark.me.delete_property('team-' + team_name)
            team_list = []
        elif team_cmd == 'remove':
            for e in emails:
                for e2 in team_list:
                    if e == e2:
                        team_list.remove(str(e.strip()))
                        out += "Removed " + e + "\n\n"
        if len(team_list) > 0:
            self.spark.me.set_property('team-' + team_name, json.dumps(team_list))
        if len(out) > 0:
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text=out,
                markdown=True)

    def messages_created(self):
        if not self.spark.room_id:
            logging.error("Got a message-created event, but roomId was not set")
            return
        if not self.spark.enrich_data('msg'):
            return
        if self.spark.room_id == self.spark.config.bot["admin_room"]:
            logging.debug("Got a message in the admin room...")
            self.admin_commands()
            return
        if self.spark.room_type == 'group':
            self.group_commands()
            return
        # There shouldn't be other room types, but just in case
        if self.spark.room_type != 'direct':
            return
        if not self.spark.me or not self.spark.me.id and self.spark.person_object == 'greger@hudya.no':
            migrate = requests.get('https://spark-army-knife.appspot.com/migration/' + self.spark.person_object,
                                   headers={
                                       'Authorization': 'Bearer 65kN%57ItPNSQVHS',
                                    })
            if migrate:
                properties = migrate.json()
                myself = actor.Actor(config=self.spark.config)
                myself.create(url=self.spark.config.root + 'bot', passphrase=self.spark.config.new_token(),
                              creator=self.spark.person_object, delete=True)
                for p, v in properties.items():
                    if p == 'migrated':
                        continue
                    if not isinstance(v, str) and not isinstance(v, unicode):
                        try:
                            v = json.dumps(v)
                        except (TypeError, KeyError, ValueError):
                            pass
                    if p == 'oauthId' and v != self.spark.person_id:
                        myself.delete()
                        logging.warning('Tried to migrate a user without the same spark id: ' +
                                        self.spark.person_object)
                        return
                    myself.set_property(p, v)
                self.spark.re_init(new_actor=myself)
                if 'firehoseId' in properties:
                    if not self.spark.link.unregister_webhook(properties['firehoseId']):
                        self.spark.link.post_bot_message(
                            email=self.spark.person_object,
                            text="Not able to re-initialize properly from old Army Knife. Please do /init",
                            markdown=True)
                        return
                msghash = hashlib.sha256()
                msghash.update(myself.passphrase)
                hook = self.spark.link.register_webhook(
                    name='Firehose',
                    target=self.spark.config.root + myself.id + '/callbacks/firehose',
                    resource='all',
                    event='all',
                    secret=msghash.hexdigest()
                )
                if hook and hook['id']:
                    logging.debug('Successfully registered messages firehose webhook')
                    myself.set_property('firehoseId', hook['id'])
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.person_object,
                        text="Not able to re-initialize properly from old Army Knife. Please do /init",
                        markdown=True)
                    return
                logging.debug("Successfully migrated " + self.spark.person_object)
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Successfully migrated your account from old Army Knife. Try with /me",
                    markdown=True)
        if self.spark.cmd == '/init':
            self.init_me()
            return
        elif self.spark.cmd == '/help':
            self.help()
            return
        elif self.spark.cmd == '/enable':
            logging.debug("Enabling account: " + self.spark.me.creator)
            self.spark.me.delete_property('app_disabled')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="The Spark Army Knife has now been enabled and will process messages and respond to commands.")
            return
        if not self.spark.me or not self.spark.me.id:
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Not able to find you as a user. Please do /init",
                markdown=True)
            return
        app_disabled = self.spark.me.get_property('app_disabled').value
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + self.spark.me.creator)
            return
        if self.spark.cmd == '/disable':
            logging.debug("Disabling account: " + self.spark.me.creator)
            self.spark.me.set_property('app_disabled', 'true')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="The Spark Army Knife has now been disabled and will not respond or process commands until you do "
                     "/enable. \n\n/enable, /help, and /init are the only commands that still work.")
            return
        elif self.spark.cmd == '/track' or self.spark.cmd == '/untrack' or self.spark.cmd == '/trackers':
            self.tracker_commands()
            return
        elif self.spark.cmd == '/myself':
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="/myself has been replaced with /me",
                markdown=True)
        elif self.spark.cmd == '/me':
            firehose = self.spark.me.get_property('firehoseId').value
            if not firehose:
                firehose = "<none>"
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="**Your Spark Army Knife Account**\n\n----\n\n" +
                     "**Registered email**: " + self.spark.me.creator + "\n\n" +
                     "**URL**: " + self.spark.config.root + self.spark.me.id + '/www\n\n' +
                     "**Webhook**: " + firehose +
                     "\n\nIf your Army Knife is fully functioning, you will also get some information about your Spark "
                     "account. If not, please do /init.",
                markdown=True)
        elif self.spark.cmd == '/delete':
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Did you also get a confirmation that all your data and account were deleted?!"
                     " (above or below this message). If not, do /init, then /delete DELETENOW again.")
        elif self.spark.cmd == '/support':
            self.spark.link.post_admin_message(
                text="From (" + self.spark.me.creator + "): " +
                     self.spark.msg_data['text'])
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Your message has been sent to support.")
        elif self.spark.cmd == '/manageteam':
            self.team_commands()
            return
        elif self.spark.cmd == '/topofmind' or self.spark.cmd == '/tom':
            self.topofmind_commands()
            return
        elif self.spark.cmd == '/recommend':
            if len(self.spark.msg_list_wcap) < 3:
                self.spark.link.post_bot_message(
                    email=self.spark.person_object,
                    text="Usage `/recommend <send_to_email> <your message to the person>,\n\n"
                         "e.g. `/recommend john@gmail.com Hey! Check out this cool app!`")
                return
            message = self.spark.msg_data['text'][
                      len(self.spark.msg_list_wcap[0]) +
                      len(self.spark.msg_list_wcap[1]) + 2:]
            self.spark.link.post_bot_message(
                email=self.spark.msg_list[1],
                text=message + "\n\n**This bot, Spark Army Knife, was recommended to you by " +
                self.spark.person_object + "**\n\nType /init to get started!",
                markdown=True)
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text=self.spark.msg_list[1] + " was just invited to use Spark Army Knife!",
                markdown=True)
            self.spark.link.post_admin_message(
                text=self.spark.msg_list[1] + " was just recommended Army Knife by " +
                self.spark.person_object)
        elif self.spark.cmd == '/autoreply':
            reply_msg = self.spark.msg_data['text'][len(self.spark.msg_list[0]):]
            self.spark.me.set_property('autoreplyMsg', reply_msg)
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Auto-reply message set to: " +
                     reply_msg + "\n\n@mentions and messages in direct rooms will now return your message.",
                markdown=True)
        elif self.spark.cmd == '/noautoreply':
            self.spark.me.delete_property('autoreplyMsg')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Auto-reply message off.")
        elif self.spark.cmd == '/nomentionalert':
            self.spark.me.set_property('no_mentions', 'true')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Alerts in the bot room for @mentions is turned off.")
        elif self.spark.cmd == '/mentionalert':
            self.spark.me.delete_property('no_mentions')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Alerts in the bot room for @mentions is turned on.")
        elif self.spark.cmd == '/noroomalert':
            self.spark.me.set_property('no_newrooms', 'true')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Alerts in the bot room for new rooms is turned off.")
        elif self.spark.cmd == '/roomalert':
            self.spark.me.delete_property('no_newrooms')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Alerts in the bot room for new rooms is turned on.")
        elif self.spark.cmd == '/noannouncements':
            self.spark.me.set_property('no_announcements', 'true')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="You will no longer get Spark Army Knife announcements.")
        elif self.spark.cmd == '/announcements':
            self.spark.me.delete_property('no_announcements')
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="You will now get Spark Army Knife announcements!")
        elif len(self.spark.msg_list) == 1 and '/' not in self.spark.cmd:
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Hi there! Unknown command. Use /help to get help.")
