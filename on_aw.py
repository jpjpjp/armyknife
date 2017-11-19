import json
import logging
import hashlib
import hmac
import datetime
from actingweb import on_aw
from spark import ciscospark
from actingweb import actor


def exec_all_users(msg_list=None, msg=None, spark=None):
    if not msg_list:
        return True
    users = actor.actors().fetch()
    if len(msg_list) < 3 or msg_list[2].lower() == 'help':
        spark.postAdminMessage("**Usage of /all-users**\n\n"
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
        return True
    cmd = msg_list[2].lower()
    counters = {}
    counters["total"] = 0
    out = ""
    if 'filter' in cmd:
        if len(msg_list) >= 4:
            filter = msg_list[3]
        else:
            spark.postAdminMessage(
                "You need to supply a filter: /all-users " + str(cmd) + " `filter value(optional)`",
                markdown=True)
            return True
    else:
        filter = None
    if filter and len(msg_list) >= 5:
        filter_value = msg_list[4]
    else:
        filter_value = None
    if cmd == "marked-message" and len(msg_list) >= 4:
        msg_markdown = msg[len(msg_list[0])+len(msg_list[1])+len(msg_list[2])+2:]
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
        spark.postAdminMessage(
            "Your /all-users command is not recognised. Please do just `/all-users` to get the help message.",
            markdown=True)
        return True
    if 'filter' in cmd:
        if not filter_value:
            out += "with attribute " + str(filter) + "**\n\n"
        elif filter_value == "None":
            out += "without attribute " + str(filter) + "**\n\n"
        else:
            out += "with attribute " + str(filter) + " containing " + str(filter_value) + "**\n\n"
    if len(out) > 0:
        spark.postAdminMessage(out, markdown=True)
        out = ""
    for u in users:
        a = actor.actor(id=u["id"])
        service_status = a.getProperty('service_status').value
        counters["total"] += 1
        if str(service_status) in counters:
            counters[str(service_status)] += 1
        else:
            counters[str(service_status)] = 1
        if cmd == "list":
            out += "**" + a.creator + "** (" + str(a.id) + "): " + str(service_status or "None") + "\n\n"
        elif filter and ('filter' in cmd):
            attr = a.getProperty(str(filter)).value
            if not attr and filter_value and filter_value == "None":
                attr = "None"
            if attr and (not filter_value or (filter_value and filter_value in attr)):
                if str(filter) in counters:
                    counters[str(filter)] += 1
                else:
                    counters[str(filter)] = 1
                if cmd == "listfilter":
                    out += "**" + a.creator + "** (" + str(a.id) + "): " + str(service_status or "None") + "\n\n"
                elif cmd == "markfilter":
                    out += a.creator + " marked.\n\n"
                    a.setProperty('filter_mark', 'true')
        elif cmd == "marked-clear":
            attr = a.getProperty('filter_mark').value
            if attr and attr == 'true':
                a.deleteProperty('filter_mark')
                if 'marked-cleared' in counters:
                    counters["marked-cleared"] += 1
                else:
                    counters["marked-cleared"] = 1
        elif cmd == "marked-list":
            attr = a.getProperty('filter_mark').value
            if attr and attr == 'true':
                out += a.creator + " (" + a.id + ")\n\n"
                if 'marked-list' in counters:
                    counters["marked-list"] += 1
                else:
                    counters["marked-list"] = 1
        elif cmd == "marked-message":
            attr = a.getProperty('filter_mark').value
            if attr and attr == 'true':
                no_alert = a.getProperty('no_announcements').value
                if not no_alert or no_alert != "true":
                    spark.postBotMessage(email=a.getProperty('email').value, text=msg_markdown, markdown=True)
                    if 'marked-messaged' in counters:
                        counters["marked-messaged"] += 1
                    else:
                        counters["marked-messaged"] = 1
        elif cmd == "marked-delete":
            attr = a.getProperty('filter_mark').value
            if attr and attr == 'true':
                out += a.creator + " deleted.\n\n"
                a.delete()
                if 'marked-deleted' in counters:
                    counters["marked-deleted"] += 1
                else:
                    counters["marked-deleted"] = 1
        if len(out) > 3000:
            spark.postAdminMessage(out, markdown=True)
            out = ""
    if len(out) > 0:
        spark.postAdminMessage(out, markdown=True)
    out = "----\n\n**Grand total number of users**: " + str(counters["total"]) + "\n\n"
    del(counters["total"])
    for k, v in counters.iteritems():
        out += str(k) + ": " + str(v) + "\n\n"
    if len(out) > 0:
        spark.postAdminMessage(out, markdown=True)
    return True


class spark_on_aw(on_aw.on_aw_base):

    @classmethod
    def bot_post(self, path):
        """Called on POSTs to /bot."""

        spark = ciscospark.ciscospark(auth=self.auth, actorId=None, config=self.config)
        rawbody = self.webobj.request.body.decode('utf-8', 'ignore')
        if not rawbody or len(rawbody) == 0:
            return False
        try:
            body = json.loads(rawbody)
            logging.debug('Bot callback: ' + rawbody)
            data = body['data']
            personId = body['actorId']
        except:
            return 405
        if 'X-Spark-Signature' in self.webobj.request.headers:
            sign = self.webobj.request.headers['X-Spark-Signature']
        else:
            sign = None
        if sign and len(sign) > 0:
            msghash = hmac.new(self.config.bot['secret'], self.webobj.request.body, digestmod=hashlib.sha1)
            if msghash.hexdigest() != sign:
                logging.warn('Signature does not match on bot message!')
                spark.postAdminMessage(text='SECURITY ALERT: Got bot message with non-matching signature')
                return 403
            else:
                logging.debug('Got signed and verified bot message')
        else:
            logging.warn('Got an unsigned bot message!')
            return 403
        if data and 'personEmail' in data:
            personObject = data['personEmail']
        else:
            # Rooms - created do not have personEmail set in data
            personObject = None
        if data and 'roomId' in data:
            roomId = data['roomId']  # id of existing room
            if 'roomType' in data:
                roomType = data['roomType']  # direct or group
            else:
                roomType = None
        elif data and 'id' in data:
            roomId = data['id']  # id of new room
            if 'type' in data:
                roomType = data['type']  # direct or group
            else:
                roomType = None
        else:
            roomId = None
        if not roomType:
            roomData = spark.getRoom(roomId)
            if roomData and 'type' in roomData:
                roomType = roomData['type']
            else:
                roomType = ''  # Unknown
        myself = actor.actor(config=self.config)
        myself.get_from_property(name='oauthId', value=personId)
        is_actor_bot = False
        if myself.id:
            logging.debug('Found actor(' + myself.id + ')')
            is_actor_user = True
            # Re-instantiate spark communciations with the proper actor
            spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id)
        else:
            is_actor_user = False
            personActor = spark.getPerson(personId)
            if personActor and 'emails' in personActor:
                if personActor['emails'][0] == self.config.bot['email']:
                    is_actor_bot = True
            else:
                logging.error("Was not able to retrieve bot callback actor person details")
                return True
        if personObject and personObject == self.config.bot['email']:
            is_bot_object = True
        else:
            is_bot_object = False
        #
        # person = id of acting person
        # roomId = either new room id or id for existing room
        # roomType = type of room
        # personActor = data on person acting (from spark.getPerson)
        # personObject = data on person acted upon (from spark.getPerson)
        # is_actor_user = True if user is an army knife user already
        # is_actor_bot = True if acting user is the bot
        # is_bot_object = True of the bot
        #
        # NOTE!!! that actor and object is the same person for messages, created events
        #
        # The first time a user is in touch with the bot, it can either be the user or the bot that has initiated
        # the contact, i.e. the acorId can either be somebody unknown or the bot
        # The message flow is the following:
        #   1. rooms, created -> type direct or group
        #   2. memberships, created -> two messages, one for the bot and one for the user
        #   3. messages, created -> either from the bot or from the user depending on who initiated the request
        #
        if not myself.id and body['resource'] == 'rooms':
            if body['event'] == 'created':
                # Don't do anything for rooms created messages
                pass
            return True
        do_init = False
        if body['resource'] == 'memberships':
            if body['event'] == 'created':
                if is_bot_object:
                    if roomType == 'group':
                        spark.postBotMessage(roomId=roomId,
                                             text="**Welcome to Spark Army Knife!**\n\n To use, please create a 1:1 room with " +
                                                  self.config.bot['email'] +
                                                  ". If already done without success, type /init in that room.",
                                             markdown=True)
                    return True
                else:
                    # The user was added
                    if roomType == 'direct':
                        do_init = True
        if body['resource'] == 'messages':
            msg = data['id']
            if body['event'] == 'created':
                if not roomId:
                    logging.error("Got a message-created event, but roomId was not set")
                    return True
                # Ignore messages from the bot itself
                if is_actor_bot:
                    return True
                msg = spark.getMessage(msg)
                roomData = spark.getRoom(roomId)
                if not msg or not roomData or 'text' not in msg or 'title' not in roomData:
                    logging.error("Was not able to retrieve message and room data from Spark for a bot message")
                    return True
                logging.debug("Received direct message: " + str(msg))
                msg_list = msg['text'].lower().split(" ")
                msg_list_wcap = msg['text'].split(" ")
                if roomType == 'direct':
                    cmd = msg_list[0]
                else:
                    if len(msg_list) < 1:
                        # No command
                        return True
                    # @mention /cmd
                    cmd = msg_list[1]
                # Admin commands
                if msg["roomId"] == self.config.bot["admin_room"]:
                    if cmd == "/mail":
                        message = msg['text'][
                                  len(msg_list_wcap[0]) + len(msg_list_wcap[1]) + len(msg_list_wcap[2]) + 3:]
                        spark.postBotMessage(email=msg_list[2], text=message)
                        spark.postAdminMessage("Sent the following message to " + msg_list[2] +
                                               ":\n\n" + message, markdown=True)
                    elif cmd == "/help":
                        spark.postAdminMessage("**Spark Army Knife: Admin Help**\n\n" \
                                               "Use `/mail <email> message` to send somebody a message from the bot.\n\n" \
                                               "Use `/all-users` for listing and messaging all users.",
                                               markdown=True)
                    elif cmd == "/all-users":
                        exec_all_users(msg_list=msg_list_wcap,
                                       msg=msg['text'], spark=spark)
                    return True
                # Group commands
                if roomType == 'group':
                    if cmd == '/help' or ('/' not in cmd and len(msg_list_wcap) <= 2):
                        spark.postBotMessage(roomId=roomId, text="**Hi there from the Spark Army Knife!**\n\n" \
                                                                 "To use, please create a 1:1 room with the bot (" +
                                                                 self.config.bot['email'] +
                                                                 ").",
                                             markdown=True)
                        if not is_actor_user:
                            spark.postBotMessage(email=personObject, text="**Hi there from the Spark Army Knife!**\n\n" \
                                                                          "Please type /init to authorize the app.",
                                                 markdown=True)
                        return True
                # Direct commands
                if data['roomType'] == 'direct':
                    if cmd == '/init':
                        do_init = True
                    elif cmd == '/help':
                        spark.postBotMessage(
                            email=personObject,
                            text="**Spark Army Knife (author: Greger Wedel)**\n\n" \
                                 "Help message for commands that only work in the bot 1:1 room.\n\n" \
                                 "**App Management**\n\n"
                                 "- Use `/init` to authorize the app.\n\n"
                                 "- Use `/delete DELETENOW` to delete your Spark Army Knife account, this room, and all data associated " \
                                 "with this account.\n\n" \
                                 "- Use `/support <message>` to send a message to support.\n\n" \
                                 "- Use `/myurl` to get the link to where your Spark Army Knife bot lives.\n\n" \
                                 "- Use `/recommend <email> <message>` to send a message to another user and recommend Spark Army Knife.\n\n" \
                                 "- Use `/nomentionalert` to turn off 1:1 bot room alerts on mentions.\n\n" \
                                 "- Use `/mentionalert` to turn on (default) 1:1 bot room alerts on mentions.\n\n" \
                                 "- Use `/noroomalert` to turn off 1:1 bot room alerts on new rooms.\n\n" \
                                 "- Use `/roomalert` to turn on (default) 1:1 bot room alerts on new rooms.\n\n" \
                                 "- Use `/noannouncements` to turn off announcements about Spark Army Knife.\n\n" \
                                 "- Use `/announcements` to turn on (default) announcements about Spark Army Knife.\n\n" \
                                 "**Top of Mind List**\n\n" \
                                 "- Use `/topofmind <index> Top of mind thing ...` to list and set your top of mind list (shortcut `/tom`).\n\n" \
                                 "- Use `/topofmind clear` to clear your top of mind list.\n\n" \
                                 "- Use `/topofmind title <Title of list>` to set the title of your top of mind list.\n\n" \
                                 "- Use `/topofmind reminder on|off` to set or stop a daily reminder of your list at this time.\n\n" \
                                 "**Box.com Integration**\n\n" \
                                 "- Use `/box <rootfolder>` to add a Box account to Spark Army Knife. " \
                                 "Optionally specify the folder where all Army Knife Box folders will be created.\n\n" \
                                 "- Use `/nobox` to disconnect and delete the Box service.\n\n" \
                                 "**Room management**\n\n" \
                                 "- Use `/countrooms` to get the number of group rooms you are a member of.\n\n" \
                                 "- Use `/checkmember <email|name>` to get a list of rooms that email or name is a member of.\n\n" \
                                 "- Use `/deletemember <email> <room-id,room-id...>` to delete a user from a room or list of rooms " \
                                 "(use Spark Id from e.g. /checkmember or /listroom).\n\n" \
                                 "- Use `/addmember <email> <room-id,room-id...>` to add a user to a room or list of rooms " \
                                 "(use Spark Id from e.g. /checkmember or /listroom).\n\n" \
                                 "- Use `/manageteam add|remove|list|delete <team_name> <email(s)>` where emails are comma-separated. " \
                                 "The team can also be initialized from members in a room, see /team command below.\n\n" \
                                 "- Use `/manageteam list` to list all teams.\n\n" \
                                 "**Messaging**\n\n" \
                                 "- Use `/track <email> <nickname>` to track messages from a person/VIP.\n\n" \
                                 "- Use `/trackers` to list tracked emails.\n\n" \
                                 "- Use `/get <nickname>` to get a list of all messages since last time for that person " \
                                 "(and `/get all` to get from all tracked people).\n\n" \
                                 "- Use `/untrack <email>` to stop tracking a person.\n\n" \
                                 "- Use `/autoreply <your_message>` to send auto-reply message to all @mentions and direct messages " \
                                 "(markdown is supported).\n\n" \
                                 "- Use `/noautoreply` to turn off auto-reply.\n\n" \
                                 "- Use `/pins` to get a list of pinned messages and reminders set with /pin command.\n\n" \
                                 "**Advanced Spark Commands**\n\n" \
                                 "- Use `/listwebhooks` to see all webhooks registered by integrations on your account.\n\n" \
                                 "- Use `/deletewebhook <webhookid>` to delete a specific webhook from /listwebhooks (**CAREFUL!!**)\n\n" \
                                 "- Use `/cleanwebhooks` to delete absolutely ALL webhooks registered for your account, not only for the " \
                                 "Army Knife (*USE WITH CAUTION!)*\n\n",
                            markdown=True)
                        spark.postBotMessage(
                            email=personObject,
                            text="- - -",
                            markdown=True)
                        spark.postBotMessage(
                            email=personObject,
                            text="Help message for commands that can be used in any room:\n\n" \
                                 "**Top of Mind List**\n\n" \
                                 "- Use `@mention /topofmind` (shortcut `/tom`) to list somebody's top of mind list.\n\n" \
                                 "- Use `/topofmind` (shortcut `/tom`) in a 1:1 room to list that person's top of mind list.\n\n" \
                                 "- Use `/topofmind subscribe` in a 1:1 room to subscribe to that person's top of mind list.\n\n" \
                                 "- Use `/topofmind unsubscribe` in a 1:1 room to unsubscribe to that person's top of mind list.\n\n" \
                                 "**Room Utility Commands**\n\n" \
                                 "- Use `/copyroom <New Title>` to create a new room with the same members as the one you are in.\n\n" \
                                 "- Use `/makepublic` to get a URL people can use to add themselves to a room. \n\n" \
                                 "- Use `/makeprivate` to disable this URL again and make the room private.\n\n" \
                                 "- Use `/listroom` to get a list of all room data for a 1:1 or group room.\n\n" \
                                 "- Use `/listfiles` to get a list of all files in a 1:1 or group room.\n\n" \
                                 "- Use `/listmembers` to get a list of all members of the current room printed in your 1:1 Army Knife bot room." \
                                 " `/listmembers csv` creates a comma separated list of email addresses.\n\n" \
                                 "- Use: `/team init|add|remove|verify|sync <team_name>` to make a new team from members in the room (init), and then " \
                                 "add, remove, or synchronize the team with a room's members. Use verify to get a list of differences.\n\n" \
                                 "**Box.com Integration**\n\n" \
                                 "- Use `/boxfolder <foldername>` in a group room to create a new Box folder and add all the room members " \
                                 "as editors to the folder. Optionally specify the name of the folder to " \
                                 "create (the room name is used default). \n\n" \
                                 "- Use `/noboxfolder` to disconnect the Box folder from the room (the folder is not deleted on Box).\n\n" \
                                 "**Reminders**\n\n" \
                                 "- Use `/pin` or `/pin <x>` to pin the previous message in a room (or the message x messages back). " \
                                 "The pinned message will be listed in your 1:1 Army Knife room.\n\n"
                                 "- Use `/pin <x> +<a>[m|h|d|w]`, to create a reminder for a message some time a into the future. " \
                                 "E.g. /pin 3 +2h, where m = minutes, h = hours, d = days, w = weeks\n\n" \
                                 "- Use `/pin 0 +<a>[m|h|d|w] <My message>` to set a reminder with no reference to a message, e.g. `/pin 0 +2h Time to leave!`\n\n",
                            markdown=True)
                    elif cmd == '/track':
                        if len(msg_list) < 3:
                            spark.postBotMessage(
                                email=personObject,
                                text="Usage: `/track <email> <nickname>`",
                                markdown=True)
                            self.webobj.response.set_status(204)
                            return True
                        added = spark.addTracker(msg_list[1], msg_list[2])
                        if added:
                            spark.postBotMessage(
                                email=personObject,
                                text="Added tracking of " + msg_list[1])
                        else:
                            spark.postBotMessage(
                                email=personObject,
                                text="Was not able to add tracking of " + msg_list[1])
                    elif cmd == '/myurl':
                        firehose = myself.getProperty('firehoseId').value
                        if not firehose:
                            firehose = "<none>"
                        spark.postBotMessage(
                            email=personObject,
                            text="**URL**: " + self.config.root + myself.id + '/www\n\n' +
                                 "**Webhook**: " + firehose,
                            markdown=True)
                    elif cmd == '/delete':
                        spark.postBotMessage(
                            email=personObject,
                            text="Did you also get a confirmation that all your data and account were deleted?! (above " \
                                 "or below this message). If not, do /init, then /delete DELETENOW again.")
                    elif cmd == '/trackers':
                        trackers = spark.loadTrackers()
                        if not trackers:
                            spark.postBotMessage(
                                email=personObject,
                                text='No people are tracked.')
                        for tracker in trackers:
                            spark.postBotMessage(
                                email=personObject,
                                text=tracker.email + ' (' + tracker.nickname + ')')
                    elif cmd == '/untrack':
                        if spark.deleteTracker(msg_list[1]):
                            spark.postBotMessage(
                                email=personObject,
                                text="Untracked " + msg_list[1])
                        else:
                            spark.postBotMessage(
                                email=personObject,
                                text="Failed untracking of " + msg_list[1])
                    elif cmd == '/support':
                        spark.postAdminMessage(text="From (" + myself.creator + "): " + msg['text'])
                        spark.postBotMessage(
                            email=personObject,
                            text="Your message has been sent to support.")
                    elif cmd == '/manageteam':
                        if len(msg_list) < 3 and not (len(msg_list) == 2 and msg_list[1] == 'list'):
                            spark.postBotMessage(
                                email=personObject,
                                text="Usage: `/manageteam add|remove|list <teamname> <email(s)>` where emails are comma-separated\n\n"
                                     "Use `/manageteam list` to list all teams",
                                markdown=True)
                            self.webobj.response.set_status(204)
                            return True
                        team_cmd = msg_list[1]
                        if len(msg_list) == 2 and team_cmd == 'list':
                            out = "**List of teams**\n\n----\n\n"
                            properties = myself.getProperties()
                            if properties and len(properties) > 0:
                                for name, value in properties.items():
                                    if 'team-' in name:
                                        try:
                                            team = json.loads(value)
                                        except ValueError:
                                            team = value
                                        out += "**" + name[len('team-'):] + "**: "
                                        sep = ""
                                        for t in team:
                                            out += sep + str(t)
                                            sep = ","
                                        out += "\n\n"
                            spark.postBotMessage(
                                email=personObject,
                                text=out,
                                markdown=True)
                            self.webobj.response.set_status(204)
                            return True
                        team_name = msg_list[2]
                        if team_cmd != 'add' and team_cmd != 'remove' and team_cmd != 'list' and team_cmd != 'delete':
                            spark.postBotMessage(
                                email=personObject,
                                text="Usage: `/manageteam add|remove|list <teamname> <email(s)>` where emails are comma-separated",
                                markdown=True)
                            self.webobj.response.set_status(204)
                            return True
                        if len(msg_list) > 3:
                            emails = msg_list[3].split(',')
                        else:
                            emails = []
                        team_str = myself.getProperty('team-' + team_name).value
                        if not team_str:
                            team_list = []
                        else:
                            try:
                                team_list = json.loads(team_str)
                            except:
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
                            out += "Deleted team " + team_name + "\n\n"
                            team_list = []
                            myself.deleteProperty('team-' + team_name)
                        elif team_cmd == 'remove':
                            for e in emails:
                                for e2 in team_list:
                                    if e == e2:
                                        team_list.remove(str(e.strip()))
                                        out += "Removed " + e + "\n\n"
                        if len(team_list) > 0:
                            myself.setProperty('team-' + team_name, json.dumps(team_list))
                        if len(out) > 0:
                            spark.postBotMessage(
                                email=personObject,
                                text=out,
                                markdown=True)
                    elif cmd == '/topofmind' or cmd == '/tom':
                        topofmind = myself.getProperty('topofmind').value
                        if topofmind:
                            try:
                                topofmind = json.loads(topofmind)
                                toplist = topofmind['list']
                            except:
                                toplist = {}
                        else:
                            toplist = {}
                            topofmind = {}
                            topofmind['email'] = myself.creator
                            topofmind['displayName'] = myself.getProperty('displayName').value
                            topofmind['title'] = "Top of Mind List"
                        # Handle no params
                        if len(msg_list) == 1 or (len(msg_list) == 2 and msg_list[1] == 'help'):
                            if len(toplist) == 0 or (len(msg_list) == 2 and msg_list[1] == 'help'):
                                spark.postBotMessage(
                                    email=personObject,
                                    text="To set an item: `/topofmind <index> <Your top of mind item>`\n\n" \
                                         "Available /topofmind commands: title, clear, reminder, x delete, x insert",
                                    markdown=True)
                                self.webobj.response.set_status(204)
                                return True
                            else:
                                out = "**" + topofmind['title'] + "**"
                                modified = myself.getProperty('topofmind_modified').value
                                if modified:
                                    timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                                    out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                                out += "\n\n---\n\n"
                                for i, el in sorted(toplist.items()):
                                    out = out + "**" + i + "**: " + el + "\n\n"
                                spark.postBotMessage(
                                    email=personObject,
                                    text=out,
                                    markdown=True)
                                self.webobj.response.set_status(204)
                                return True
                        # Handle more than one param
                        index = msg_list_wcap[1]
                        if index == "clear":
                            myself.deleteProperty('topofmind')
                            topofmind['list'] = {}
                            out = json.dumps(topofmind)
                            myself.registerDiffs(target='properties', subtarget='topofmind', blob=out)
                            spark.postBotMessage(
                                email=personObject,
                                text="Cleared your " + topofmind['title'])
                            self.webobj.response.set_status(204)
                            return True
                        if index == "subscriptions":
                            subs = myself.getSubscriptions(target='properties', subtarget='topofmind', callback=True)
                            if len(subs) > 0:
                                out = "**Your Top Of Mind subscriptions on others**\n\n"
                            else:
                                out = ''
                            for s in subs:
                                out += "Subscription " + s["subscriptionid"] + " on peer " + s["peerid"] + "\n\n"
                            subs = None
                            subs = myself.getSubscriptions(target='properties', subtarget='topofmind', callback=False)
                            if len(subs) > 0:
                                out += "----\n\n**Others subscribing to your Top Of Mind**\n\n"
                            for s in subs:
                                out += "Subscription " + s["subscriptionid"] + " from peer " + s["peerid"] + "\n\n"
                            if len(out) > 0:
                                spark.postBotMessage(
                                    email=personObject,
                                    text=out,
                                    markdown=True)
                            else:
                                spark.postBotMessage(
                                    email=personObject,
                                    text="There are no subscriptions.",
                                    markdown=True)
                            self.webobj.response.set_status(204)
                            return True
                        if index == "title":
                            if len(msg_list_wcap) < 3:
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Use: /topofmind title <Your new list title>")
                                self.webobj.response.set_status(204)
                                return True
                            topofmind['title'] = msg['text'][len(msg_list_wcap[0]) + len(msg_list_wcap[1]) + 2:]
                            out = json.dumps(topofmind)
                            myself.setProperty('topofmind', out)
                            spark.postBotMessage(
                                email=personObject,
                                text="Set top of mind list title to " + topofmind['title'])
                            self.webobj.response.set_status(204)
                            return True
                        if index == "reminder":
                            if len(msg_list_wcap) != 3:
                                spark.postBotMessage(
                                    email=personObject,
                                    text="You must use reminder on or off! (/topofmind reminder on|off)")
                                self.webobj.response.set_status(204)
                                return True
                            if msg_list_wcap[2] == "on":
                                spark.deletePinnedMessages(comment="#/TOPOFMIND")
                                now = datetime.datetime.utcnow()
                                targettime = now + datetime.timedelta(days=1)
                                spark.savePinnedMessage(comment='#/TOPOFMIND', timestamp=targettime)
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Set reminder of top of mind list at this time each day")
                            elif msg_list_wcap[2] == "off":
                                spark.deletePinnedMessages(comment="#/TOPOFMIND")
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Deleted daily reminder of " + topofmind['title'])
                            self.webobj.response.set_status(204)
                            return True
                        if index:
                            listitem = msg['text'][len(msg_list_wcap[0]) + len(msg_list_wcap[1]) + 2:]
                            now = datetime.datetime.now()
                            myself.setProperty('topofmind_modified', now.strftime('%Y-%m-%d %H:%M'))
                            if listitem == "delete":
                                del (toplist[index])
                                spark.postBotMessage(
                                    email=personObject,
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
                                        spark.postBotMessage(
                                            email=personObject,
                                            text="**Inserted list item " + str(index) + "** with text " + listitem,
                                            markdown=True)
                                except ValueError:
                                    spark.postBotMessage(
                                        email=personObject,
                                        text="You cannot use insert command when you have list item(s) that have text as index.",
                                        markdown=True)
                            else:
                                toplist[index] = listitem
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Added list item **" + str(index) + "** with text `" + toplist[index] + "`",
                                    markdown=True)
                            topofmind['list'] = toplist
                            out = json.dumps(topofmind, sort_keys=True)
                            myself.setProperty('topofmind', out)
                            myself.registerDiffs(target='properties', subtarget='topofmind', blob=out)
                    elif cmd == '/recommend':
                        if len(msg_list_wcap) < 3:
                            spark.postBotMessage(
                                email=personObject,
                                text="Usage `/recommend <send_to_email> <your message to the person>,\n\n" \
                                     "e.g. `/recommend john@gmail.com Hey! Check out this cool app!`")
                            self.webobj.response.set_status(204)
                            return True
                        message = msg['text'][len(msg_list_wcap[0]) + len(msg_list_wcap[1]) + 2:]
                        spark.postBotMessage(
                            email=msg_list[1],
                            text=message + "\n\n**Recommended to you by " + personObject + "**\n\nType /init to get started!",
                            markdown=True)
                        spark.postBotMessage(
                            email=personObject,
                            text=msg_list[1] + " was just invited to use Spark Army Knife!",
                            markdown=True)
                        spark.postAdminMessage(text=msg_list[1] + " was just recommended Army Knife by " + personObject)
                    elif cmd == '/autoreply':
                        reply_msg = msg['text'][len(msg_list[0]):]
                        myself.setProperty('autoreplyMsg', reply_msg)
                        spark.postBotMessage(
                            email=personObject,
                            text="Auto-reply message set to: " +
                                 reply_msg + "\n\n@mentions and messages in direct rooms will now return your message.",
                            markdown=True)
                    elif cmd == '/noautoreply':
                        myself.deleteProperty('autoreplyMsg')
                        spark.postBotMessage(
                            email=personObject,
                            text="Auto-reply message off.")
                    elif cmd == '/nomentionalert':
                        myself.setProperty('no_mentions', 'true')
                        spark.postBotMessage(
                            email=personObject,
                            text="Alerts in the bot room for @mentions is turned off.")
                    elif cmd == '/mentionalert':
                        myself.deleteProperty('no_mentions')
                        spark.postBotMessage(
                            email=personObject,
                            text="Alerts in the bot room for @mentions is turned on.")
                    elif cmd == '/noroomalert':
                        myself.setProperty('no_newrooms', 'true')
                        spark.postBotMessage(
                            email=personObject,
                            text="Alerts in the bot room for new rooms is turned off.")
                    elif cmd == '/roomalert':
                        myself.deleteProperty('no_newrooms')
                        spark.postBotMessage(
                            email=personObject,
                            text="Alerts in the bot room for new rooms is turned on.")
                    elif cmd == '/noannouncements':
                        myself.setProperty('no_announcements', 'true')
                        spark.postBotMessage(
                            email=personObject,
                            text="You will no longer get Spark Army Knife announcements.")
                    elif cmd == '/announcements':
                        myself.deleteProperty('no_announcements')
                        spark.postBotMessage(
                            email=personObject,
                            text="You will now get Spark Army Knife announcements!")
                    elif len(msg_list) == 1 and '/' not in cmd:
                        spark.postBotMessage(
                            email=personObject,
                            text="Hi there! Use /help to get help. /init to authorize the app.")
        # Now execute on actions set above
        if do_init:
            if not myself.id:
                # Use delete=True here as we haven't found an actor with the right oauthId at this
                # point, so any existing actors have issues
                myself.create(url=self.config.root, creator=personObject,
                              passphrase=self.config.newToken(), delete=True)
            url = self.config.root + myself.id
            myself.setProperty('chatRoomId', roomId)
            if not is_actor_user:
                spark.postMessage(roomId, "**Welcome to Spark Army Knife, " + personObject +
                                  "!**\n\n Please authorize the app by clicking the following link: " +
                                  url + "/www",
                                  markdown=True)
            else:
                spark.postMessage(roomId, "Welcome back!\n\n" \
                                          "Please re-authorize the app by clicking the following link: " +
                                  url + "/www?refresh=true",
                                  markdown=True)
        return True

    def get_callbacks(self, name):
        """Customizible function to handle GET /callbacks"""
        # return True if callback has been processed
        # THE BELOW IS SAMPLE CODE
        #my_oauth=oauth.oauth(token = myself.getProperty('oauth_token').value)
        # if name == 'something':
        #    return
        # END OF SAMPLE CODE
        return False

    def delete_callbacks(self, name):
        """Customizible function to handle DELETE /callbacks"""
        # return True if callback has been processed
        return False

    def post_callbacks(self, name):
        """Customizible function to handle POST /callbacks"""
        # return True if callback has been processed
        # THE BELOW IS SAMPLE CODE
        #logging.debug("Callback body: "+self.webobj.request.body.decode('utf-8', 'ignore'))
        # non-json POSTs to be handled first
        # if name == 'somethingelse':
        #    return True
        # Handle json POSTs below
        #body = json.loads(self.webobj.request.body.decode('utf-8', 'ignore'))
        #data = body['data']
        # if name == 'somethingmore':
        #    callback_id = self.webobj.request.get('id')
        #    self.webobj.response.set_status(204)
        #    return True
        #self.webobj.response.set_status(403, "Callback not found.")
        # END OF SAMPLE CODE
        return False


    def post_subscriptions(self, sub, peerid, data):
        """Customizible function to process incoming callbacks/subscriptions/ callback with json body, return True if processed, False if not."""
        logging.debug("Got callback and processed " + sub["subscriptionid"] +
                      " subscription from peer " + peerid + " with json blob: " + json.dumps(data))
        return True

    def delete_actor(self):
        # THIS METHOD IS CALLED WHEN AN ACTOR IS REQUESTED TO BE DELETED.
        # THE BELOW IS SAMPLE CODE
        # Clean up anything associated with this actor before it is deleted.
        # END OF SAMPLE CODE
        return

    @classmethod
    def check_on_oauth_success(self, token=None):
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        me = spark.getMe()
        if not me:
            logging.debug("Not able to retrieve myself from Spark!")
            return False
        logging.debug("My identity:" + me['id'])
        currentId = self.myself.getProperty('oauthId')
        if not currentId.value:
            if 'emails' not in me:
                self.myself.deleteProperty('cookie_redirect')
                return False
            if self.myself.creator != me['emails'][0]:
                self.myself.deleteProperty('cookie_redirect')
                self.myself.deleteProperty('oauth_token')
                self.myself.deleteProperty('oauth_refresh_token')
                self.myself.deleteProperty('oauth_token_expiry')
                self.myself.deleteProperty('oauth_refresh_token_expiry')
                spark.postBotMessage(
                    email=me['emails'][0],
                    text="**WARNING!!**\n\nAn attempt to create a new Spark Army Knife account for " + self.myself.creator +
                         " was done while you were logged into Cisco Spark in your browser. Did you try with the wrong email address?\n\n"
                         "You can instead do /init here to (re)authorize your account (click the link to grant new access).",
                    markdown=True)
                spark.postBotMessage(
                    email=self.myself.creator,
                    text="**SECURITY WARNING**\n\n" + me['emails'][0] +
                         "'s Spark credentials were attempted used to create a new Spark Army Knife account for you.\n\n"
                         "No action required, but somebody may have attempted to hijack your Spark Army Knife account.",
                    markdown=True)
                if not self.myself.getProperty('oauthId').value:
                    self.myself.delete()
                return False
            self.myself.setProperty('email', me['emails'][0])
            self.myself.setProperty('oauthId', me['id'])
            if 'displayName' in me:
                self.myself.setProperty('displayName', me['displayName'])
            if 'avatar' in me:
                self.myself.setProperty('avatarURI', me['avatar'])
            if '@actingweb.net' not in me['emails'][0]:
                spark.postAdminMessage(
                    text='New user just signed up: ' + me['displayName'] + ' (' + me['emails'][0] + ')')
        else:
            logging.debug("Actor's identity:" + currentId.value)
            if me['id'] != currentId.value:
                self.myself.deleteProperty('cookie_redirect')
                self.myself.deleteProperty('oauth_token')
                self.myself.deleteProperty('oauth_refresh_token')
                self.myself.deleteProperty('oauth_token_expiry')
                self.myself.deleteProperty('oauth_refresh_token_expiry')
                spark.postBotMessage(
                    email=self.myself.getProperty('email').value,
                    text="**SECURITY WARNING**\n\n" + (me['emails'][0] or "Unknown") +
                         " tried to log into your Spark Army Knife account.\n\n"
                         "For security reasons, your Spark Army Knife account has been suspended.\n\n"
                         "If this happens repeatedly, please contact support@greger.io",
                    markdown=True)
                return False
        return True

    @classmethod
    def actions_on_oauth_success(self):
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        email = self.myself.getProperty('email').value
        hookId = self.myself.getProperty('firehoseId').value
        self.myself.deleteProperty('token_invalid')
        self.myself.deleteProperty('service_status')
        if not hookId:
            msghash = hashlib.sha256()
            msghash.update(self.myself.passphrase)
            hook = spark.registerWebHook(name='Firehose', target=self.config.root + self.myself.id + '/callbacks/firehose',
                                         resource='all', event='all',
                                         secret=msghash.hexdigest())
            if hook and hook['id']:
                logging.debug('Successfully registered messages firehose webhook')
                self.myself.setProperty('firehoseId', hook['id'])
            else:
                logging.debug('Failed to register messages firehose webhook')
                spark.postAdminMessage(text='Failed to register firehose: ' + email)
        chatRoom = self.myself.getProperty('chatRoomId').value
        if not chatRoom:
            msg = spark.postBotMessage(
                email=email,
                text="Hi there! Welcome to the **Spark Army Knife**! \n\n" \
                     "You have successfully authorized access.\n\nSend me commands starting with /. Like /help",
                markdown=True)
            if not msg or 'roomId' not in msg:
                logging.warn("Not able to create 1:1 bot room after oauth success.")
                return False
            self.myself.setProperty('chatRoomId', msg['roomId'])
        else:
            spark.postBotMessage(
                roomId=chatRoom,
                text="Hi there! You have successfully authorized this app!\n\n Send me commands starting with /. Like /help")
        return True

    def get_resources(self, name):
        """ Called on GET to resources. Return struct for json out.

            Returning {} will give a 404 response back to requestor.
        """
        return {}

    def delete_resources(self, name):
        """ Called on DELETE to resources. Return struct for json out.

            Returning {} will give a 404 response back to requestor.
        """
        return {}

    def put_resources(self, name, params):
        """ Called on PUT to resources. Return struct for json out.

            Returning {} will give a 404 response back to requestor.
            Returning an error code after setting the response will not change
            the error code.
        """
        return {}

    def post_resources(self, name, params):
        """ Called on POST to resources. Return struct for json out.

            Returning {} will give a 404 response back to requestor.
            Returning an error code after setting the response will not change
            the error code.
        """
        return {}

    def www_paths(self, path=''):
        # THIS METHOD IS CALLED WHEN AN actorid/www/* PATH IS CALLED (AND AFTER ACTINGWEB DEFAULT PATHS HAVE BEEN HANDLED)
        # THE BELOW IS SAMPLE CODE
        # if path == '' or not myself:
        #    logging.info('Got an on_www_paths without proper parameters.')
        #    return False
        # if path == 'something':
        #    return True
        # END OF SAMPLE CODE
        return False
