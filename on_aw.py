import json
import logging
import hashlib
import hmac
import datetime
import re
import base64
from actingweb import on_aw
from actingweb import auth as auth_class
from actingweb import aw_proxy
from armyknife import ciscospark
from armyknife import armyknife
from actingweb import actor


def check_member(mail, target, spark):
    out = ""
    next_rooms = spark.getRooms()
    rooms = []
    while next_rooms and 'items' in next_rooms:
        rooms.extend(next_rooms['items'])
        next_rooms = spark.getRooms(get_next=True)
    if len(rooms) > 0:
        out += "**You are member of " + str(len(rooms)) + " group rooms**\n\n"
        out += "Searching for rooms with " + target + " as a member...\n\n"
    else:
        out += "**No rooms found**"
    spark.postBotMessage(
        email=mail,
        text=out,
        markdown=True)
    out = ""
    nr_of_rooms = 0
    found_in_rooms = 0
    for r in rooms:
        next_members = spark.getMemberships(id=str(r['id']))
        nr_of_rooms += 1
        members = []
        while next_members and 'items' in next_members:
            members.extend(next_members['items'])
            next_members = spark.getMemberships(get_next=True)
        if len(members) > 0:
            for r in members:
                if ('@' in target and 'personEmail' in r and target in r['personEmail'].lower()) or ('@' not in target and 'personDisplayName' in r and target in r['personDisplayName'].lower()):
                    found_in_rooms += 1
                    room = spark.getRoom(id=str(r['roomId']))
                    if room and 'title' in room:
                        out += room['title'] + " (" + r['roomId'] + ")"
                    else:
                        out += "Unknown title (" + r['roomId'] + ")"
                    out += "\n"
                    if len(out) > 2000:
                        spark.postBotMessage(
                            email=mail,
                            text=out)
                        out = ""
                    break
    if len(out) > 0:
        spark.postBotMessage(
            email=mail,
            text=out)
    spark.postBotMessage(
        email=mail,
        text="----\n\nSearched " + str(nr_of_rooms) + " rooms, and found " + target + " in " + str(found_in_rooms) + " rooms.",
        markdown=True)


def exec_all_users(msg_list=None, msg=None, spark=None, config=None):
    if not msg_list:
        return True
    users = actor.actors(config=config).fetch()
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
        a = actor.actor(id=u["id"], config=config)
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
    def delete_actor(self):
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        store = armyknife.armyknife(actorId=self.myself.id, config=self.config)
        store.clearMessages(email=self.myself.creator)
        trackers = store.loadTrackers()
        for tracker in trackers:
            store.deleteTracker(tracker["email"])
        chatRoom = self.myself.getProperty('chatRoomId')
        if chatRoom and chatRoom.value:
            spark.postMessage(
                chatRoom.value, "**Deleting all your data and account.**\n\nThe 1:1 room with the bot will remain." \
                                " Type /init there if you want to create a new account.",
                markdown=True)
            spark.deleteRoom(chatRoom.value)
        firehoseId = self.myself.getProperty('firehoseId')
        if firehoseId and firehoseId.value:
            spark.unregisterWebHook(firehoseId.value)
        store.deleteRooms()
        store.deletePinnedMessages()
        store.deletePinnedMessages(comment="#/TOPOFMIND")
        if '@actingweb.net' not in self.myself.creator and self.myself.creator != "creator" and self.myself.creator != "trustee":
            spark.postAdminMessage(text='User just left: ' + self.myself.creator)
        return

    @classmethod
    def www_paths(self, path=''):
        if path == '' or not self.myself:
            logging.info('Got an on_www_paths without proper parameters.')
            return False
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        if path == 'getattachment':
            self.webobj.response.template_values = {
                'url': str(self.webobj.request.get('url')),
                'filename': str(self.webobj.request.get('filename')),
            }
            return True
        return False


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
            spark = ciscospark.ciscospark(auth=self.auth, actorId=myself.id, config=self.config)
            store = armyknife.armyknife(actorId=myself.id, config=self.config)
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
                                       msg=msg['text'], spark=spark, config=self.config)
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
                        person = spark.getPerson()
                        added = store.addTracker(msg_list[1], msg_list[2])
                        if added:
                            spark.postBotMessage(
                                email=personObject,
                                text="Added tracking of " + msg_list[1])
                        else:
                            spark.postBotMessage(
                                email=personObject,
                                text="Was not able to add tracking of " + msg_list[1])
                    elif cmd == '/myurl':
                        if not myself.id:
                            spark.postBotMessage(
                                email=personObject,
                                text="Not able to find you as a user. Please do /init",
                                markdown=True)
                            return True
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
                        trackers = store.loadTrackers()
                        if not trackers:
                            spark.postBotMessage(
                                email=personObject,
                                text='No people are tracked.')
                        for tracker in trackers:
                            spark.postBotMessage(
                                email=personObject,
                                text=tracker["email"] + ' (' + tracker["nickname"] + ')')
                    elif cmd == '/untrack':
                        if store.deleteTracker(msg_list[1]):
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
                                text="Usage: `/manageteam add|remove|list|delete <teamname> <email(s)>` where emails are comma-separated",
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
                                store.deletePinnedMessages(comment="#/TOPOFMIND")
                                now = datetime.datetime.utcnow()
                                targettime = now + datetime.timedelta(days=1)
                                store.savePinnedMessage(comment='#/TOPOFMIND', timestamp=targettime)
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Set reminder of top of mind list at this time each day")
                            elif msg_list_wcap[2] == "off":
                                store.deletePinnedMessages(comment="#/TOPOFMIND")
                                spark.postBotMessage(
                                    email=personObject,
                                    text="Deleted daily reminder of " + topofmind['title'])
                            self.webobj.response.set_status(204)
                            return True
                        if index:
                            listitem = msg['text'][len(msg_list_wcap[0]) + len(msg_list_wcap[1]) + 2:]
                            now = datetime.datetime.utcnow()
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
        if not self.myself:
            logging.debug("Got a firehose callback for an unknown user.")
            return True
        else:
            myself=self.myself
        spark = ciscospark.ciscospark(auth=self.auth, actorId=myself.id, config=self.config)
        email = myself.getProperty('email').value
        hookId = myself.getProperty('firehoseId').value
        myself.deleteProperty('token_invalid')
        myself.deleteProperty('service_status')
        if not hookId or not spark.getWebHook(hookId):
            msghash = hashlib.sha256()
            msghash.update(myself.passphrase)
            hook = spark.registerWebHook(name='Firehose', target=self.config.root + myself.id + '/callbacks/firehose',
                                         resource='all', event='all',
                                         secret=msghash.hexdigest())
            if hook and hook['id']:
                logging.debug('Successfully registered messages firehose webhook')
                myself.setProperty('firehoseId', hook['id'])
            else:
                logging.debug('Failed to register messages firehose webhook')
                spark.postAdminMessage(text='Failed to register firehose: ' + email)
        chatRoom = myself.getProperty('chatRoomId').value
        if not chatRoom:
            msg = spark.postBotMessage(
                email=email,
                text="Hi there! Welcome to the **Spark Army Knife**! \n\n" \
                     "You have successfully authorized access.\n\nSend me commands starting with /. Like /help",
                markdown=True)
            if not msg or 'roomId' not in msg:
                logging.warn("Not able to create 1:1 bot room after oauth success.")
                return False
            myself.setProperty('chatRoomId', msg['roomId'])
        else:
            spark.postBotMessage(
                roomId=chatRoom,
                text="Hi there! You have successfully authorized this app!\n\n Send me commands starting with /. Like /help")
        return True

    @classmethod
    def get_callbacks(self, name):
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        store = armyknife.armyknife(actorId=self.myself.id, config=self.config)
        if name == 'joinroom':
            uuid = self.webobj.request.get('id')
            room = store.loadRoomByUuid(uuid)
            if not room:
                self.webobj.response.set_status(404)
                return True
            roominfo = spark.getRoom(room['id'])
            self.webobj.response.template_values = {
                'id': uuid,
                'title': roominfo['title'],
            }
        if name == 'makefilepublic':
            pass
            # This is not secure!!! So do not execute
            # token is exposed directly in javascript in the users browser

            #self.webobj.response.template_values = {
            #    'url': str(self.webobj.request.get('url')),
            #    'token': str(auth.token),
            #    'filename': str(self.webobj.request.get('filename')),
            # }
        return True

    @classmethod
    def post_callbacks(self, name):
        if not self.myself:
            logging.debug("Got a firehose callback for an unknown user.")
            return True
        else:
            myself=self.myself
            auth = self.auth
            webobj = self.webobj
        spark = ciscospark.ciscospark(auth=auth, actorId=myself.id, config=self.config)
        store = armyknife.armyknife(actorId=myself.id, config=self.config)
        logging.debug("Callback body: " + webobj.request.body.decode('utf-8', 'ignore'))
        chatRoomId = myself.getProperty('chatRoomId').value
        # Clean up any actor creations from earlier where we got wrong creator email
        if myself.creator == self.config.bot['email'] or myself.creator == "creator":
            my_email = myself.getProperty('email').value
            if my_email and len(my_email) > 0:
                myself.modify(creator=my_email)
        # Deprecated support for /callbacks/room
        if name == 'room':
            self.webobj.response.set_status(404)
            return True
        # non-json POSTs to be handled first
        if name == 'joinroom':
            uuid = self.webobj.request.get('id')
            email = self.webobj.request.get('email')
            room = store.loadRoomByUuid(uuid)
            roominfo = spark.getRoom(room['id'])
            self.webobj.response.template_values = {
                'title': roominfo['title'],
            }
            if not spark.addMember(id=room['id'], email=email):
                spark.postBotMessage(
                    email=myself.creator,
                    text="Failed adding new member " +
                         email + " to room " + roominfo['title'])
                self.webobj.response.template_values["template_path"] = 'spark-joinedroom-failed.html'
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Added new member " + email + " to room " + roominfo['title'])
                self.webobj.response.template_values["template_path"] = 'spark-joinedroom.html'
            return True
        # Handle json POSTs below
        body = json.loads(self.webobj.request.body.decode('utf-8', 'ignore'))
        data = body['data']
        if 'roomId' in data:
            responseRoomId = data['roomId']
        else:
            responseRoomId = chatRoomId
        now = datetime.datetime.utcnow()
        myOauthId = myself.getProperty('oauthId').value
        if myself.getProperty('autoreplyMsg').value:
            reply_msg = "Via armyknife@sparkbot.io auto-reply:\n\n" + myself.getProperty('autoreplyMsg').value
        else:
            reply_msg = None
        service_status = myself.getProperty('service_status').value
        if not service_status:
            myself.setProperty('service_status', 'firehose')
        # validateOAuthToken() returns the redirect URL if token cannot be refreshed
        if len(auth.validateOAuthToken(lazy=True)) > 0:
            if not service_status or service_status != 'invalid':
                myself.setProperty('service_status', 'invalid')
            logging.info("Was not able to automatically refresh token.")
            token_invalid = myself.getProperty('token_invalid').value
            if not token_invalid or token_invalid != now.strftime("%Y%m%d"):
                myself.setProperty('token_invalid', now.strftime("%Y%m%d"))
                spark.postBotMessage(
                    email=myself.creator,
                    text="Your Spark Army Knife account has no longer access. Please type " \
                         "/init in this room to re-authorize the account.")
                spark.postBotMessage(
                    email=myself.creator,
                    text="If you repeatedly get this error message, do /delete DELETENOW " \
                         "before a new /init. This will reset your account (note: all settings as well).")
                logging.info("User (" + myself.creator + ") has invalid refresh token and got notified.")
            self.webobj.response.set_status(202, "Accepted, but not processed")
            return True
        # This is a special section that uses firehose for all messages to retrieve pinned messages
        # to see if anything needs to be processed (for other actors than the one receiving the firehose)
        due = store.getDuePinnedMessages()
        for m in due:
            pin_owner = actor.actor(id=m["actorId"], config=self.config)
            auth2 = auth_class.auth(id=m["actorId"], config=self.config)
            spark2 = ciscospark.ciscospark(auth=auth2, actorId=m["actorId"], config=self.config)
            email_owner = pin_owner.getProperty(name='email').value
            if len(m["comment"]) == 0:
                m["comment"] = "ARMY KNIFE REMINDER"
            if m["id"] and len(m["id"]) > 0:
                pin = spark2.getMessage(id=m["id"])
                if not pin:
                    logging.warn('Not able to retrieve message data for pinned message')
                    spark2.postBotMessage(
                        email=email_owner,
                        text="You had a pinned reminder, but it was not possible to retrieve details."
                    )
                    continue
                person = spark2.getPerson(id=pin['personId'])
                room = spark2.getRoom(id=pin['roomId'])
                if not person or not room:
                    logging.warn('Not able to retrieve person and room data for pinned message')
                    spark2.postBotMessage(
                        email=email_owner,
                        text="You had a pinned reminder, but it was not possible to retrieve details."
                    )
                    continue
                spark2.postBotMessage(
                    email=email_owner,
                    text="**PIN ALERT!! - " + m["comment"] + "**\n\n" \
                                                          "From " + person['displayName'] + " (" + person['emails'][
                             0] + ")" + " in room (" + room['title'] + ")\n\n" +
                         pin['text'] + "\n\n",
                    markdown=True)
            else:
                if m["comment"] == '#/TOPOFMIND':
                    topofmind = pin_owner.getProperty('topofmind').value
                    if topofmind:
                        try:
                            topofmind = json.loads(topofmind)
                            toplist = topofmind['list']
                        except:
                            toplist = {}
                    else:
                        toplist = None
                    if toplist:
                        out = "**Your Daily Top of Mind Reminder**"
                        modified = pin_owner.getProperty('topofmind_modified').value
                        if modified:
                            timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                            out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                        out += "\n\n---\n\n"
                        for i, el in sorted(toplist.items()):
                            out = out + "**" + i + "**: " + el + "\n\n"
                        spark2.postBotMessage(
                            email=email_owner,
                            text=out,
                            markdown=True)
                    spark2.deletePinnedMessages(comment="#/TOPOFMIND")
                    targettime = m["timestamp"] + datetime.timedelta(days=1)
                    spark2.savePinnedMessage(comment='#/TOPOFMIND', timestamp=targettime)
                else:
                    spark2.postBotMessage(
                        email=email_owner,
                        text="**PIN ALERT!! - " + m["comment"] + "**",
                        markdown=True)
        if 'X-Spark-Signature' in webobj.request.headers:
            sign = webobj.request.headers['X-Spark-Signature']
        else:
            sign = None
        if sign and len(sign) > 0:
            myhash = hashlib.sha256()
            myhash.update(myself.passphrase)
            msghash = hmac.new(myhash.hexdigest(), webobj.request.body, digestmod=hashlib.sha1)
            if msghash.hexdigest() == sign:
                logging.debug('Signature matches')
            else:
                logging.debug('Signature does not match ' + str(sign))
                # Do not accept this message as it may be an attacker
                self.webobj.response.set_status(403, "Forbidden")
                return True
        if name == 'firehose':
            if body['resource'] == 'messages':
                if body['event'] == 'created':
                    # Ignore all messages from sparkbots
                    if "@sparkbot.io" in data['personEmail'].lower():
                        self.webobj.response.set_status(204)
                        return True
                    if data['roomType'] == 'direct' and reply_msg and data['personEmail'] != myself.creator:
                        # Retrieve the last user we responded to and don't reply if it's the same user
                        lastAutoReply = myself.getProperty('autoreplyMsg-last').value
                        if lastAutoReply and lastAutoReply == data['personEmail'].lower():
                            self.webobj.response.set_status(204)
                            return True
                        else:
                            myself.setProperty('autoreplyMsg-last', data['personEmail'].lower())
                        msg = spark.getMessage(data['id'])
                        if not msg or 'text' not in msg:
                            myself.setProperty('service_status', 'invalid')
                            lastErr = spark.lastResponse()
                            logging.warn(
                                "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                                ") - " + lastErr['message'])
                            return False
                        if "armyknife@sparkbot.io" in msg['text']:
                            self.webobj.response.set_status(204)
                            return True
                        personSender = spark.getPerson(id=data['personId'])
                        spark.postMessage(
                            data['roomId'], reply_msg, markdown=True)
                        if 'displayName' not in personSender:
                            personSender = {}
                            personSender['displayName'] = "Unknown name"
                        spark.postBotMessage(email=myself.creator,
                                             text="**" + personSender['displayName'] + " (" +
                                                  data['personEmail'] +
                                                  ") sent a 1:1 message to you (auto-replied to) " +
                                                  ":**\n\n" +
                                                  msg['text'], markdown=True)
                        reply_msg = None
                        self.webobj.response.set_status(204)
                        return True
                    mentioned = False
                    if 'mentionedPeople' in data:
                        for person in data['mentionedPeople']:
                            if person == myOauthId:
                                mentioned = True
                                if reply_msg:
                                    spark.postMessage(
                                        data['roomId'], reply_msg, markdown=True)
                                    reply_on = '(auto-replied to)'
                                else:
                                    reply_on = ''
                                room = spark.getRoom(data['roomId'])
                                msg = spark.getMessage(data['id'])
                                personMentioning = spark.getPerson(id=data['personId'])
                                if not room or not msg or not personMentioning:
                                    myself.setProperty('service_status', 'invalid')
                                    lastErr = spark.lastResponse()
                                    logging.warn(
                                        "Error in getting direct message from spark callback. Code(" + str(
                                            lastErr['code']) +
                                        ") - " + lastErr['message'])
                                    return False
                                if 'title' in room and 'text' in msg:
                                    no_alert = myself.getProperty('no_mentions').value
                                    if not no_alert or no_alert.lower() != 'true':
                                        spark.postBotMessage(email=myself.creator,
                                                             text="**" + personMentioning['displayName'] + " (" +
                                                                  data['personEmail'] +
                                                                  ") mentioned you " + reply_on + " in the room " +
                                                                  room['title'] + ":**\n\n" +
                                                                  msg['text'], markdown=True)
                    if (data['roomType'] == 'direct' or mentioned) and data['personEmail'] != myself.creator:
                        msg = spark.getMessage(data['id'])
                        if not msg or 'text' not in msg:
                            myself.setProperty('service_status', 'invalid')
                            lastErr = spark.lastResponse()
                            logging.warn(
                                "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                                ") - " + lastErr['message'])
                            return False
                        if not service_status or service_status == 'invalid' or service_status == 'firehose':
                            myself.setProperty('service_status', 'active')
                        me = spark.getMe()
                        message = msg['text']
                        if 'displayName' in me:
                            userName = me['displayName']
                            if mentioned:
                                message = msg['text'][len(userName) + 1:]
                                logging.debug('-' + message + '-')
                        else:
                            userName = 'No Name Available'
                        tokens = message.split(' ')
                        if tokens[0] == '/topofmind' or tokens[0] == '/tom':
                            topofmind = myself.getProperty('topofmind').value
                            toplist = None
                            if topofmind:
                                try:
                                    topofmind = json.loads(topofmind)
                                    toplist = topofmind['list']
                                except:
                                    toplist = None
                            if len(tokens) == 1:
                                if toplist and len(toplist) > 0:
                                    out = "**" + topofmind['title'] + " for " + userName + "**"
                                    modified = myself.getProperty('topofmind_modified').value
                                    if modified:
                                        timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                                        out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                                    out += "\n\n---\n\n"
                                    for i, el in sorted(toplist.items()):
                                        out = out + "**" + i + "**: " + el + "\n\n"
                                    spark.postBotMessage(
                                        email=data['personEmail'],
                                        text=out,
                                        markdown=True)
                                else:
                                    spark.postBotMessage(
                                        email=data['personEmail'],
                                        text="No available top of mind list",
                                        markdown=True)
                                    toplist = None
                            elif len(tokens) == 2 and tokens[1].lower() == 'subscribe':
                                # myself is now the owner of the topofmind
                                # data['personEmail'] is the person wanting to subscribe
                                subscriber_email = data['personEmail']
                                subscriber = actor.actor(config=self.config)
                                subscriber.get_from_property(name='email', value=subscriber_email)
                                if not subscriber.id:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Failed in looking up your Spark Army Knife account. Please type /init here"
                                             " and authorize Spark Army Knife.")
                                    self.webobj.response.set_status(204)
                                    return True
                                peerid = myself.id
                                logging.debug("Looking for existing peer trust:(" + str(peerid) + ")")
                                trust = subscriber.getTrustRelationship(peerid=peerid)
                                if not trust:
                                    trust = subscriber.createReciprocalTrust(
                                        url=self.config.actors['myself']['factory'] + str(peerid), secret=self.config.newToken(),
                                        desc="Top of mind subscriber", relationship="associate",
                                        type=self.config.type)
                                    if trust:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Created trust relationship for top of mind subscription.")
                                else:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Trust relationship for top of mind subscription was already established.")
                                if not trust:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Creation of trust relationship for top of mind subscription failed.\n\n"
                                             "Cannot create subscrition.")
                                else:
                                    sub = subscriber.getSubscriptions(peerid=trust['peerid'], target='properties',
                                                                      subtarget='topofmind', callback=True)
                                    if len(sub) > 0:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Top of mind subscription was already created.")
                                    else:
                                        sub = subscriber.createRemoteSubscription(peerid=trust['peerid'],
                                                                                  target='properties',
                                                                                  subtarget='topofmind',
                                                                                  granularity='high')
                                        if not sub:
                                            spark.postBotMessage(
                                                email=subscriber_email,
                                                text="Creation of new top of mind subscription failed.")
                                        else:
                                            spark.postBotMessage(
                                                email=subscriber_email,
                                                text="Created top of mind subscription for " + myself.creator + ".")
                            elif len(tokens) == 2 and tokens[1].lower() == 'unsubscribe':
                                # myself is now the owner of the topofmind
                                # data['personEmail'] is the person wanting to unsubscribe
                                subscriber_email = data['personEmail']
                                subscriber = actor.actor(config=self.config)
                                subscriber.get_from_property(name='email', value=subscriber_email)
                                if not subscriber.id:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Failed in looking up your Spark Army Knife account.")
                                    self.webobj.response.set_status(204)
                                    return True
                                # My subscriptions
                                subs = subscriber.getSubscriptions(
                                    peerid=myself.id,
                                    target='properties',
                                    subtarget='topofmind',
                                    callback=True)
                                if len(subs) >= 1:
                                    if not subscriber.deleteRemoteSubscription(peerid=myself.id,
                                                                               subid=subs[0]['subscriptionid']):
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Failed cancelling the top of mind subscription on your peer.")
                                    elif not subscriber.deleteSubscription(peerid=myself.id,
                                                                           subid=subs[0]['subscriptionid']):
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Failed cancelling your top of mind subscription.")
                                    else:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Cancelled the top of mind subscription.")
                                # Subscriptions on me
                                subs2 = subscriber.getSubscriptions(
                                    peerid=myself.id,
                                    target='properties',
                                    subtarget='topofmind',
                                    callback=False)
                                if len(subs2) == 0:
                                    if not subscriber.deleteReciprocalTrust(peerid=myself.id, deletePeer=True):
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Failed cancelling the trust relationship.")
                                    else:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Deleted the trust relationship.")
            if body['resource'] == 'memberships':
                if body['event'] == 'created' and ('personEmail' in data and data['personEmail'] == myself.creator):
                    room = spark.getRoom(data['roomId'])
                    if room and 'title' in room:
                        no_alert = myself.getProperty('no_newrooms').value
                        if not no_alert or no_alert.lower() != 'true':
                            spark.postBotMessage(email=myself.creator,
                                                 text="You were added to the room " + room['title'])
                    self.webobj.response.set_status(204)
                    return True
                room = store.loadRoom(data['roomId'])
                if room and room["boxFolderId"]:
                    box = myself.getPeerTrustee(shorttype='boxbasic')
                    proxy = aw_proxy.aw_proxy(peer_target=box)
                    if body['event'] == 'created':
                        params = {
                            'collaborations': [
                                {
                                    'email': data['personEmail'],
                                },
                            ],
                        }
                    elif body['event'] == 'deleted':
                        params = {
                            'collaborations': [
                                {
                                    'email': data['personEmail'],
                                    'action': 'delete',
                                },
                            ],
                        }
                    proxy.changeResource(path='resources/folders/' + room["boxFolderId"], params=params)
                    if proxy.last_response_code < 200 or proxy.last_response_code > 299:
                        logging.warn('Unable to add/remove collaborator(' + data['personEmail'] +
                                     ') to Box folder(' + room["boxFolderId"] + ')')
                    else:
                        logging.debug('Added/removed collaborator(' + data['personEmail'] +
                                      ') to Box folder(' + room["boxFolderId"] + ')')
        # Below here we only handle messages:created events, so don't process anything else
        if body['resource'] != 'messages' or body['event'] != 'created':
            self.webobj.response.set_status(204)
            return True
        store.processMessage(data)
        # This is not a message from myself
        if data['personId'] != myOauthId:
            self.webobj.response.set_status(204)
            return True
        msg = spark.getMessage(data['id'])
        if not msg or 'text' not in msg:
            myself.setProperty('service_status', 'invalid')
            lastErr = spark.lastResponse()
            logging.warn(
                "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                ") - " + lastErr['message'])
            return False
        if not service_status or service_status == 'invalid' or service_status == 'firehose':
            myself.setProperty('service_status', 'active')
        msg_list = msg['text'].lower().split(" ")
        msg_list_wcap = msg['text'].split(" ")
        if msg_list[0] == '/pin':
            spark.deleteMessage(data['id'])
            if len(msg_list) >= 2:
                try:
                    nr = int(msg_list[1]) - 1
                except:
                    spark.postMessage(
                        id=responseRoomId,
                        text="In `/pin x +a[m|h|d|w] Your message`, x and a must be digits, using 1 for x.",
                        markdown=True)
                    nr = 0
                if nr < 0:
                    # Typed in 0 means no message
                    nr = None
            else:
                nr = 0
            if nr > 10:
                max = nr + 1
            else:
                max = 10
            targettime = None
            comment = None
            if len(msg_list) > 2:
                if len(msg_list) > 3:
                    comment = msg['text'][len(msg_list[0]) + len(msg_list[1]) + len(msg_list[2]) + 3:]
                if '+' in msg_list[2]:
                    deltalist = re.split('[m|h|d[w]', msg_list[2][1:])
                    if deltalist:
                        delta = int(deltalist[0])
                    else:
                        delta = 1
                    typelist = re.split('\d+', msg_list[2])
                    if deltalist and len(deltalist) == 2:
                        deltatype = typelist[1]
                    else:
                        deltatype = 'd'
                else:
                    spark.postMessage(
                        id=responseRoomId,
                        text="Usage: `/pin x +a[m|h|d|w] Your message`, e.g. /pin 3 +2h, where m = minutes, h = hours, d = days, w = weeks" \
                             "       Use x=0 to set a reminder with no reference to a message, e.g. `/pin 0 +2h Time to leave!`",
                        markdown=True)
                    self.webobj.response.set_status(204)
                    return True
                now = datetime.datetime.utcnow()
                if deltatype == 'm':
                    targettime = now + datetime.timedelta(minutes=delta)
                elif deltatype == 'h':
                    targettime = now + datetime.timedelta(hours=delta)
                elif deltatype == 'w':
                    targettime = now + datetime.timedelta(days=(delta * 7))
                else:
                    targettime = now + datetime.timedelta(days=delta)
            if nr is not None:
                msgs = spark.getMessages(roomId=responseRoomId, beforeId=data['id'], max=max)
            if targettime:
                if nr is not None:
                    store.savePinnedMessage(id=msgs[nr]['id'], comment=comment, timestamp=targettime)
                else:
                    store.savePinnedMessage(comment=comment, timestamp=targettime)
            elif nr is not None:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**Pinned (" + msgs[nr]['created'] + ") from " +
                         msgs[nr]['personEmail'] + ":** " + msgs[nr]['text'],
                    markdown=True)
        elif msg_list[0] == '/makepublic' and responseRoomId != chatRoomId:
            uuid = store.addUUID2room(responseRoomId)
            if not uuid:
                spark.postMessage(
                    id=responseRoomId,
                    text="Failed to make room public")
            else:
                spark.postMessage(
                    id=responseRoomId, text="Public URI: " + self.config.root +
                                            myself.id + '/callbacks/joinroom?id=' + uuid)
        elif msg_list[0] == '/makeprivate' and responseRoomId != chatRoomId:
            if not store.deleteFromRoom(responseRoomId, uuid=True):
                spark.postMessage(
                    id=responseRoomId,
                    text="Failed to make room private.")
            else:
                spark.postMessage(
                    id=responseRoomId,
                    text="Made room private and add URL will not work anymore.")
        elif msg_list[0] == '/listroom' and responseRoomId != chatRoomId:
            spark.deleteMessage(data['id'])
            room = spark.getRoom(id=responseRoomId)
            msg = ''
            for key in room:
                msg = msg + "**" + str(key) + "**: " + str(room[key]) + "\n\n"
                if key == 'id':
                    id2 = base64.b64decode(room[key]).split("ROOM/")
                    if len(id2) >= 2:
                        msg = msg + "**Web URL**:" + " https://web.ciscospark.com/rooms/" + id2[1] + "\n\n"
            if len(msg) > 0:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**Room Details**\n\n" + msg +
                         "\n\nUse `/listmembers` and `/listfiles` to get other room details.",
                    markdown=True)
        elif msg_list[0] == '/listfiles' and responseRoomId != chatRoomId:
            spark.deleteMessage(data['id'])
            feature_toggles = myself.getProperty('featureToggles').value
            msgs = spark.getMessages(roomId=responseRoomId, max=200)
            room = spark.getRoom(id=responseRoomId)
            if 'title' in room:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**Files in room: " + room['title'] + "**\n\n",
                    markdown=True)
            while msgs:
                for msg in msgs:
                    if 'files' in msg:
                        for file in msg['files']:
                            details = spark.getAttachmentDetails(file)
                            if 'content-disposition' in details:
                                filename = re.search(ur"filename[^;\n=]*=(['\"])*(?:utf-8\'\')?(.*)(?(1)\1|)",
                                                     details['content-disposition']).group(2)
                            else:
                                filename = 'unknown'
                            timestamp = datetime.datetime.strptime(msg['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            time = timestamp.strftime('%Y-%m-%d %H:%M')
                            if 'content-length' in details:
                                size = int(details['content-length']) / 1024
                            else:
                                size = 'x'
                            if True or feature_toggles and ('listfiles' in feature_toggles or 'beta' in feature_toggles):
                                spark.postBotMessage(
                                    email=myself.creator,
                                    text=time + ": [" + filename + " (" + str(size) + " KB)](" + self.config.root +
                                         myself.id + '/www/getattachment?url=' + file + "&filename=" + filename + ")",
                                    markdown=True)
                            else:
                                spark.postBotMessage(
                                    email=myself.creator,
                                    text=time + ": " + filename + " (" + str(size) + " KB)",
                                    markdown=True)
                # Using max=0 gives us the next batch
                msgs = spark.getMessages(roomId=responseRoomId, max=0)
        elif msg_list[0] == '/listwebhooks' and responseRoomId == chatRoomId:
            spark.postBotMessage(
                email=myself.creator,
                text="**All Registered Webhooks on Your Account**\n\n- - -",
                markdown=True)
            ret = spark.getAllWebHooks()
            while 1:
                if not ret:
                    break
                for h in ret['webhooks']:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="**Name(id)**: " + h['name'] + " (" + h['id'] + ")"
                                                                             "\n\n**Events**: " + h['resource'] + ":" +
                             h['event'] +
                             "\n\n**Target**: " + h['targetUrl'] +
                             "\n\n**Created**: " + h['created'] +
                             "\n\n- - -\n\n",
                        markdown=True
                    )
                if not ret['next']:
                    break
                ret = spark.getAllWebHooks(uri=ret['next'])
        elif msg_list[0] == '/deletewebhook' and responseRoomId == chatRoomId:
            if len(msg_list) != 2:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage `/deletewebook <webhookid>`.\n\nUse /listwebhooks to get the id."
                )
            else:
                hookId = msg_list_wcap[1]
                ret = spark.unregisterWebHook(id=hookId)
                if ret is not None:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Deleted webhook: " + hookId
                    )
                else:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Was not able to delete webhook: " + hookId
                    )
        elif msg_list[0] == '/cleanwebhooks' and responseRoomId == chatRoomId:
            myself.deleteProperty('firehoseId')
            spark.cleanAllWebhooks(id=responseRoomId)
            spark.postBotMessage(
                email=myself.creator,
                text="Started cleaning up ALL webhooks.")
            hook = spark.registerWebHook(
                name='Firehose',
                target=self.config.root + myself.id + '/callbacks/firehose',
                resource='all',
                event='all')
            if hook and hook['id']:
                logging.debug('Successfully registered messages firehose webhook')
                myself.setProperty('firehoseId', hook['id'])
        elif msg_list[0] == '/countrooms' and responseRoomId == chatRoomId:
            out = "**Counting rooms...**\n\n----\n\n"
            next_rooms = spark.getRooms()
            rooms = []
            while next_rooms and 'items' in next_rooms:
                rooms.extend(next_rooms['items'])
                next_rooms = spark.getRooms(get_next=True)
            if len(rooms) > 0:
                out += "**You are member of " + str(len(rooms)) + " group rooms**\n\n"
            else:
                out += "**No rooms found**"
            spark.postBotMessage(
                email=myself.creator,
                text=out,
                markdown=True)
        elif msg_list[0] == '/checkmember' and responseRoomId == chatRoomId:
            if len(msg_list) == 1:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/checkmember <email>` to check room memberships for the email",
                    markdown=True)
                self.webobj.response.set_status(204)
                return True
            else:
                target = msg_list[1]
            spark.postBotMessage(
                email=myself.creator,
                text="**Room memberships for " + target + "**\n\n----\n\n",
                markdown=True)
            check_member(myself.creator, target, spark)
        elif msg_list[0] == '/deletemember' and responseRoomId == chatRoomId:
            if len(msg_list) < 3:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/deletemember <email> <room-id>` to delete user with <email> from a room with <room-id>.",
                    markdown=True)
                self.webobj.response.set_status(204)
                return True
            target = msg_list[1]
            ids = msg_list_wcap[2].split(',')
            for i in ids:
                next_members = spark.getMemberships(id=str(i))
                members = []
                while next_members and 'items' in next_members:
                    members.extend(next_members['items'])
                    next_members = spark.getMemberships(get_next=True)
                found = False
                for m in members:
                    found = False
                    if m['personEmail'].lower() == target:
                        found = True
                        res = spark.deleteMember(id=m['id'])
                        if res != None:
                            spark.postBotMessage(
                                email=myself.creator,
                                text="Deleted " + target + " from the room " + i,
                                markdown=True)
                        else:
                            spark.postBotMessage(
                                email=myself.creator,
                                text="Delete failed from the room " + i,
                                markdown=True)
                        break
                if not found:
                    spark.postBotMessage(
                        email=myself.creator,
                        text=target + " was not found in room " + i,
                        markdown=True)
        elif msg_list[0] == '/addmember' and responseRoomId == chatRoomId:
            if len(msg_list) < 3:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/addmember <email> <room-id>` to add user with <email> to a room with <room-id>.",
                    markdown=True)
                self.webobj.response.set_status(204)
                return True
            ids = msg_list_wcap[2].split(',')
            logging.debug(str(msg_list_wcap))
            for i in ids:
                res = spark.addMember(id=i, email=msg_list[1])
                if res != None:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Added " + msg_list[1] + " to the room " + i,
                        markdown=True)
                else:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Failed adding " + msg_list[1] + " to room " + i,
                        markdown=True)
        elif msg_list[0] == '/get' and responseRoomId == chatRoomId:
            if len(msg_list) == 1:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/get <all|nickname>` to get messages from all or from a special nickname.",
                    markdown=True)
                self.webobj.response.set_status(204)
                return True
            if len(msg_list) == 2 and msg_list[1] == 'all':
                trackers = store.loadTrackers()
                nicknames = []
                for tracker in trackers:
                    nicknames.append(tracker["nickname"])
            else:
                nicknames = [msg_list[1]]
            for nick in nicknames:
                msgs = store.loadMessages(nickname=nick)
                if not msgs:
                    spark.postBotMessage(
                        email=myself.creator,
                        text='**No messages from ' +
                             nick + '**', markdown=True)
                else:
                    spark.postBotMessage(
                        email=myself.creator,
                        text='-------- -------- --------- --------- ---------')
                    spark.postBotMessage(
                        email=myself.creator,
                        text='**Messages from: ' +
                             nick + '**', markdown=True)
                    for msg in msgs:
                        msgContent = spark.getMessage(msg["id"])
                        if not msgContent:
                            continue
                        text = msgContent['text']
                        room = spark.getRoom(msg["roomId"])
                        spark.postBotMessage(
                            email=myself.creator,
                            text=msg["timestamp"].strftime('%c') + ' - (' + room['title'] + ')' + '\r\n' + text)
                    store.clearMessages(nickname=nick)
        elif msg_list[0] == '/listmembers' and responseRoomId != chatRoomId:
            spark.deleteMessage(data['id'])
            if len(msg_list) == 2 and msg_list[1] == 'csv':
                csv = True
            else:
                csv = False
            members = spark.getMemberships(id=responseRoomId)
            if 'items' not in members:
                logging.info("Not able to retrieve members for room in /listmembers")
                spark.postMessage(
                    id=responseRoomId,
                    text="Net able to retrieve members in room to list members.")
                self.webobj.response.set_status(204)
                return True
            memberlist = ""
            sep = ""
            for m in members['items']:
                if csv:
                    memberlist = memberlist + sep + m['personEmail']
                    sep = ","
                else:
                    memberlist = memberlist + "\n\n" + m['personDisplayName'] + " (" + m['personEmail'] + ")"
            room = spark.getRoom(id=responseRoomId)
            if 'title' in room:
                memberlist = "**Members in room: " + room['title'] + "**\n\n----\n\n" + memberlist
            spark.postBotMessage(
                email=myself.creator,
                text=memberlist, markdown=True)
        elif msg_list[0] == '/delete' and responseRoomId == chatRoomId:
            if len(msg_list) == 2 and msg_list[1] == 'deletenow':
                self.delete_actor()
                myself.delete()
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/delete DELETENOW`", markdown=True)
        elif msg_list[0] == '/pins' and responseRoomId == chatRoomId:
            msgs = store.getPinnedMessages()
            if msgs:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**Your Pinned Reminders (all times are in UTC)**\n\n----\n\n",
                    markdown=True)
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**You have no Pinned Reminders**",
                    markdown=True)
            for m in msgs:
                if len(m["id"]) == 0:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="**" + m["timestamp"].strftime('%Y-%m-%d %H:%M') + "** -- " + m["comment"] + "\n\n----\n\n",
                        markdown=True)
                    continue
                pin = spark.getMessage(id=m["id"])
                if not pin:
                    logging.warn('Not able to retrieve message data for pinned message ')
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Not possible to retrieve pinned message details."
                    )
                    continue
                person = spark.getPerson(id=pin['personId'])
                room = spark.getRoom(id=pin['roomId'])
                if not person or not room:
                    logging.warn('Not able to retrieve person and room data for pinned message')
                    spark.postBotMessage(
                        email=myself.creator,
                        text="Not possible to retrieve pinned message person and room details."
                    )
                    continue
                spark.postBotMessage(
                    email=myself.creator,
                    text="**" + m["timestamp"].strftime('%Y-%m-%d %H:%M') + "** -- " + m["comment"] + "\n\nFrom " +
                         person['displayName'] + " (" + person['emails'][0] + ")" + " in room (" + room[
                             'title'] + ")\n\n" +
                         pin['text'] + "\n\n----\n\n",
                    markdown=True)
        elif msg_list[0] == '/team' and responseRoomId != chatRoomId:
            spark.deleteMessage(data['id'])
            if len(msg_list) != 3:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Usage: `/team init|add|remove|verify|sync team_name`", markdown=True)
                self.webobj.response.set_status(204)
                return True
            team_cmd = msg_list[1]
            team_name = msg_list[2]
            team_str = myself.getProperty('team-' + team_name).value
            if not team_str:
                team_list = []
            else:
                try:
                    team_list = json.loads(team_str)
                except:
                    team_list = []
            members = spark.getMemberships(id=responseRoomId)
            roomData = spark.getRoom(id=responseRoomId)
            if roomData and 'title' in roomData:
                title = roomData['title']
            else:
                title = 'Unknown'
            if 'items' not in members:
                logging.info("Not able to retrieve members for room in /team")
                spark.postBotMessage(
                    email=myself.creator,
                    text="Not able to get members of room.")
                self.webobj.response.set_status(204)
                return True
            out = ''
            if team_cmd == 'init':
                team_list = []
                out = "**Initializing team " + team_name + " with members from room " + title + "**\n\n"
                for m in members['items']:
                    out += "Added " + m['personEmail'] + "\n\n"
                    team_list.append(str(m['personEmail']))
                if len(team_list) > 0:
                    myself.setProperty('team-' + team_name, json.dumps(team_list))
            elif team_cmd == 'add' or team_cmd == 'remove' or team_cmd == 'verify' or team_cmd == 'sync':
                if len(team_list) == 0:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="You tried to use /team with a non-existent team.")
                else:
                    if team_cmd == 'add':
                        out = "**Adding "
                    elif team_cmd == 'remove':
                        out = "**Removing "
                    elif team_cmd == 'sync':
                        out = "**Synchronizing "
                    else:
                        out = "**Verifying "
                    out += "team members from " + team_name + " in room " + title + "**\n\n"
                    for m in members['items']:
                        try:
                            team_list.remove(m['personEmail'])
                            if team_cmd == 'remove':
                                spark.deleteMember(id=m['id'])
                                out += "Removed from room: " + m['personEmail'] + "\n\n"
                        except:
                            if team_cmd == 'verify':
                                out += "In room, but not in team: " + m['personEmail'] + "\n\n"
                            elif team_cmd == 'sync':
                                out += "Removed from room: " + m['personEmail'] + "\n\n"
                                spark.deleteMember(id=m['id'])
                    for e in team_list:
                        if team_cmd == 'add' or team_cmd == 'sync':
                            spark.addMember(id=responseRoomId, email=e)
                            out += "Added to room " + e + "\n\n"
                        elif team_cmd == 'verify':
                            out += "Not in room, but in team: " + e + "\n\n"
            spark.postBotMessage(
                email=myself.creator,
                text=out,
                markdown=True)
        elif msg_list[0] == '/copyroom' and responseRoomId != chatRoomId:
            # Only allow copyroom in group rooms
            if data['roomType'] == 'direct':
                self.webobj.response.set_status(204)
                return True
            if len(msg_list) == 1:
                spark.postMessage(
                    id=responseRoomId,
                    text="Usage: `/copyroom New Room Title`", markdown=True)
                self.webobj.response.set_status(204)
                return True
            title = msg['text'][len(msg_list[0]) + 1:]
            roomData = spark.getRoom(id=responseRoomId)
            if roomData and 'teamId' in roomData:
                teamId = roomData['teamId']
            else:
                teamId = None
            room = spark.createRoom(title, teamId)
            if not room:
                spark.postMessage(
                    id=responseRoomId,
                    text="Not able to create new room.")
                self.webobj.response.set_status(204)
                return True
            members = spark.getMemberships(id=responseRoomId)
            if 'items' not in members:
                logging.info("Not able to retrieve members for room in /copyroom")
                spark.postMessage(
                    id=responseRoomId,
                    text="Created room, but not able to add members.")
                self.webobj.response.set_status(204)
                return True
            for m in members['items']:
                spark.addMember(id=room['id'], personId=m['personId'])
            spark.postMessage(
                id=responseRoomId,
                text="Created new room and added the same members as in this room.")
        elif msg_list[0] == '/box' and responseRoomId == chatRoomId:
            box = myself.getPeerTrustee(shorttype='boxbasic')
            if not box:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Failed to create new box service.")
                self.webobj.response.set_status(204)
                return True
            if len(msg_list) > 1:
                boxRootId = myself.getProperty('boxRootId').value
                if boxRootId:
                    spark.postBotMessage(
                        email=myself.creator,
                        text="You have created the Box root folder in Box and started to use it. " \
                             "You must do /nobox before you can change root folder.")
                    self.webobj.response.set_status(204)
                    return True
                boxRoot = msg_list_wcap[1]
            else:
                boxRoot = myself.getProperty('boxRoot').value
                if not boxRoot:
                    boxRoot = 'SparkRoomFolders'
            myself.setProperty('boxRoot', boxRoot)
            spark.postBotMessage(
                email=myself.creator,
                text="Your box service is available and can be authorized at " + box['baseuri'] +
                     "/www\n\n" +
                     "Then use /boxfolder in group rooms to create new Box folders (created below the " +
                     boxRoot + " folder).")
        elif msg_list[0] == '/boxfolder' and responseRoomId != chatRoomId:
            # boxRoot is set when issueing the /box command
            boxRoot = myself.getProperty('boxRoot').value
            if not boxRoot or len(boxRoot) == 0:
                spark.postMessage(
                    id=responseRoomId,
                    text="You have not authorized the Box service. Go to the 1:1 bot room and do the /box command first.")
                self.webobj.response.set_status(204)
                return True
            box = myself.getPeerTrustee(shorttype='boxbasic')
            proxy = aw_proxy.aw_proxy(peer_target=box, config=self.config)
            # boxRootId is set the first time a /boxfolder command is run
            boxRootId = myself.getProperty('boxRootId').value
            if not boxRootId:
                # Create the root folder
                params = {
                    'name': boxRoot,
                }
                rootFolder = proxy.createResource(
                    path='/resources/folders',
                    params=params)
                if rootFolder and 'id' in rootFolder:
                    boxRootId = rootFolder['id']
                    myself.setProperty('boxRootId', boxRootId)
                else:
                    if 'error' in rootFolder and rootFolder['error']['code'] == 401:
                        spark.postMessage(
                            id=responseRoomId,
                            text="You need to authorize the Box service first. Do /box from the 1:1 bot room.")
                    elif 'error' in rootFolder and rootFolder['error']['code'] == 409:
                        spark.postMessage(
                            id=responseRoomId,
                            text="The folder already exists in Box. Delete it, or choose a different name root folder (/nobox, then /box anothername)")
                    elif 'error' in rootFolder and rootFolder['error']['code'] != 401:
                        spark.postMessage(
                            id=responseRoomId,
                            text="Failed to create the Box root folder (" + rootFolder['error']['message'] + ")")
                    else:
                        spark.postMessage(
                            id=responseRoomId,
                            text="Unknown error trying to create Box root folder.")
                    self.webobj.response.set_status(204)
                    return True
            room = store.loadRoom(responseRoomId)
            if room and len(room["boxFolderId"]) > 0:
                folder = proxy.getResource('resources/folders/' + room["boxFolderId"])
                if folder and 'url' in folder:
                    spark.postMessage(
                        id=responseRoomId,
                        text='The box folder name for this room is **' +
                             folder['name'] + '**, and can be found at: ' +
                             folder['url'], markdown=True)
                else:
                    spark.postMessage(
                        id=responseRoomId,
                        text="Unable to retrieve shared link from Box for this room's folder")
                self.webobj.response.set_status(204)
                return True
            # /boxfolder <rootfoldername>
            if len(msg_list) > 1:
                folderName = msg_list_wcap[1]
            else:
                room = spark.getRoom(responseRoomId)
                folderName = room['title']
            params = {
                'name': folderName,
                'parent': boxRootId,
            }
            emails = spark.getMemberships(id=responseRoomId)
            # Create the params['email'] list
            if emails and emails['items']:
                params['emails'] = []
                for item in emails['items']:
                    if item['isMonitor'] or item['personEmail'] == myself.creator:
                        continue
                    params['emails'].append(item['personEmail'])
            folder = proxy.createResource(
                path='/resources/folders',
                params=params)
            if folder and 'url' in folder:
                url = folder['url']
            else:
                url = 'No shared link available'
            if folder and 'id' in folder and 'error' not in folder:
                sub = myself.createRemoteSubscription(
                    peerid=box['peerid'],
                    target='resources',
                    subtarget='folders',
                    resource=folder['id'],
                    granularity='high')
                spark.postMessage(
                    id=responseRoomId,
                    text="Created a new box folder for this room with name: " + folderName +
                         " and shared link: " + url + ". Also added all room members as editors.")
                store.add2Room(roomId=responseRoomId, boxFolderId=folder['id'])
            else:
                if folder and 'error' in folder:
                    if 'url' in folder:
                        spark.postMessage(
                            id=responseRoomId,
                            text='The box folder for this room can be found at: ' + folder['url'])
                    else:
                        spark.postMessage(
                            id=responseRoomId,
                            text=folder['error']['message'])
                else:
                    spark.postMessage(
                        id=responseRoomId,
                        text='Failed to create new folder for unknown reason.')
        elif msg_list[0] == '/noboxfolder' and responseRoomId != chatRoomId:
            room = store.loadRoom(responseRoomId)
            if not room:
                spark.postMessage(
                    id=responseRoomId,
                    text="You don't have a box folder for this room. Do /boxfolder [foldername] to" \
                         " create one. \n\nDefault folder name is the room name.")
            else:
                box = myself.getPeerTrustee(shorttype='boxbasic')
                proxy = aw_proxy.aw_proxy(peer_target=box, config=self.config)
                if not proxy.deleteResource('resources/folders/' + room["boxFolderId"]):
                    spark.postMessage(
                        id=responseRoomId,
                        text="Failed to disconnect the Box folder from this room.")
                else:
                    store.deleteFromRoom(responseRoomId, boxfolder=True)
                    spark.postMessage(
                        id=responseRoomId,
                        text="Disconnected the Box folder from this room. The Box folder was not deleted.")
        elif msg_list[0] == '/nobox' and responseRoomId == chatRoomId:
            if not myself.deletePeerTrustee(shorttype='boxbasic'):
                spark.postBotMessage(
                    email=myself.creator,
                    text="Failed to delete box service.")
            else:
                myself.deleteProperty('boxRoot')
                myself.deleteProperty('boxRootId')
                boxRooms = store.loadRooms()
                for b in boxRooms:
                    store.deleteFromRoom(b.id, boxfolder=True)
                spark.postBotMessage(
                    email=myself.creator,
                    text="Deleted your box service.")
        self.webobj.response.set_status(204)
        return True

    @classmethod
    def post_subscriptions(self, sub, peerid, data):
        """Customizible function to process incoming callbacks/subscriptions/ callback with json body,
            return True if processed, False if not."""
        logging.debug("Got callback and processed " + sub["subscriptionid"] +
                      " subscription from peer " + peerid + " with json blob: " + json.dumps(data))
        spark = ciscospark.ciscospark(auth=self.auth, actorId=self.myself.id, config=self.config)
        if 'target' in data and data['target'] == 'properties':
            if 'subtarget' in data and data['subtarget'] == 'topofmind' and 'data' in data:
                topofmind = data['data']
                toplist = topofmind['list']
                if len(toplist) == 0:
                    spark.postBotMessage(
                        email=self.myself.creator,
                        text=topofmind['displayName'] + " (" + topofmind['email'] + ") just cleared " +
                             topofmind['title'], markdown=True)
                    return True
                out = topofmind['displayName'] + " (" + topofmind['email'] + ") just updated " + topofmind[
                    'title'] + "\n\n----\n\n"
                for i, el in sorted(toplist.items()):
                    out = out + "**" + i + "**: " + el + "\n\n"
                spark.postBotMessage(email=self.myself.creator, text=out, markdown=True)
            return True
        if 'resource' in data:
            folder_id = data['resource']
            room = store.loadRoomByBoxFolderId(folder_id=folder_id)
            if room and 'data' in data and 'suggested_txt' in data['data']:
                spark.postMessage(room.id, '**From Box:** ' + data['data']['suggested_txt'], markdown=True)
            else:
                logging.warn('Was not able to post callback message to Spark room.')
        else:
            logging.debug('No resource in received subscription data.')
        return True
