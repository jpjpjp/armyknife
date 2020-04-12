import json
import datetime
import logging
import re
import base64
import hashlib
from armyknife_src import ciscowebexteams
from armyknife_src import armyknife
from armyknife_src import fargate
from actingweb import actor
from actingweb import auth
from actingweb import aw_proxy
from . import payments


class WebexTeamsMessageHandler:
    """ Class with all methods to handle messages that are associated directly with a user through OAuth

    This is called a Cisco Webex Teams integration and is mostly handled through registering a webhook callback on the
    event types that the integration should receive. Here it is called a firehose. """

    def __init__(self, spark=None, webobj=None):
        self.spark = spark
        self.webobj = webobj

    def check_member(self, target, quiet=False):
        out = ""
        next_rooms = self.spark.link.get_rooms()
        rooms = []
        while next_rooms and 'items' in next_rooms:
            rooms.extend(next_rooms['items'])
            next_rooms = self.spark.link.get_rooms(get_next=True)
        if len(rooms) > 0:
            out += "You are member of " + str(len(rooms)) + " group rooms\n\n"
            out += "Searching for rooms with " + target + " as a member (this may take a long time)...\n\n"
        else:
            out += "**No rooms found**"
        if not quiet:
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text=out,
                markdown=True)
        out = ""
        nr_of_rooms = 0
        found_in_rooms = 0
        list_of_rooms = []
        for r in rooms:
            next_members = self.spark.link.get_memberships(spark_id=str(r['id']))
            nr_of_rooms += 1
            members = []
            while next_members and 'items' in next_members:
                members.extend(next_members['items'])
                next_members = self.spark.link.get_memberships(get_next=True)
            if len(members) > 0:
                for m in members:
                    if ('@' in target and 'personEmail' in m and target in m['personEmail'].lower()) or \
                            ('@' not in target and 'personDisplayName' in m and target in m[
                                'personDisplayName'].lower()):
                        found_in_rooms += 1
                        list_of_rooms.append(r['id'])
                        room = self.spark.link.get_room(spark_id=str(r['id']))
                        if room and 'title' in room:
                            out += room['title'] + " (" + r['id'] + ")"
                        else:
                            out += "Unknown title (" + r['id'] + ")"
                        out += "\n"
                        if len(out) > 2000:
                            self.spark.link.post_bot_message(
                                email=self.spark.me.creator,
                                text=out)
                            out = ""
                        break
        if len(out) > 0 and not quiet:
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text=out)
        if not quiet:
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="----\n\nSearched " + str(nr_of_rooms) + " rooms, and found " + target + " in " +
                     str(found_in_rooms) +
                     " rooms.",
                markdown=True)
        return found_in_rooms, list_of_rooms

    def joinroom(self):
        uuid = self.webobj.request.get('id')
        email = self.webobj.request.get('email')
        room = self.spark.store.load_room_by_uuid(uuid)
        roominfo = self.spark.link.get_room(room['id'])
        self.webobj.response.template_values = {
            'title': roominfo['title'],
        }
        if not self.spark.link.add_member(spark_id=room['id'], email=email):
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Failed adding new member " +
                     email + " to room " + roominfo['title'])
            self.webobj.response.template_values["template_path"] = 'spark-joinedroom-failed.html'
            return False
        else:
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Added new member " + email + " to room " + roominfo['title'])
            self.webobj.response.template_values["template_path"] = 'spark-joinedroom.html'
        return True

    def global_actions(self):
        """ Do actions that are not related to a specific user """
        due = self.spark.store.get_due_pinned_messages()
        for m in due:
            pin_owner = actor.Actor(actor_id=m["actor_id"], config=self.spark.config)
            per_user_auth = auth.Auth(actor_id=m["actor_id"], config=self.spark.config)
            per_user_spark = ciscowebexteams.CiscoWebexTeams(auth=per_user_auth, actor_id=m["actor_id"],
                                                             config=self.spark.config)
            email_owner = pin_owner.store.email
            app_disabled = pin_owner.property.app_disabled
            if app_disabled and app_disabled.lower() == 'true':
                logging.debug("Account is disabled: " + email_owner)
                continue
            per_user_store = armyknife.ArmyKnife(actor_id=m["actor_id"], config=self.spark.config)
            if len(m["comment"]) == 0:
                m["comment"] = "ARMY KNIFE REMINDER"
            # handle top of mind reminders first, marked with a special comment
            if m["comment"] == '#/TOPOFMIND':
                topofmind = pin_owner.property.topofmind
                if topofmind:
                    try:
                        topofmind = json.loads(topofmind, strict=False)
                        toplist = topofmind['list']
                    except (TypeError, KeyError, ValueError):
                        toplist = {}
                else:
                    toplist = None
                if toplist:
                    out = "**Your Daily Top of Mind Reminder**"
                    modified = pin_owner.property.topofmind_modified
                    if modified:
                        timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                        out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                    out += "\n\n---\n\n"
                    for i, el in sorted(toplist.items()):
                        out = out + "**" + str(i) + "**: " + str(el) + "\n\n"
                    per_user_spark.post_bot_message(
                        email=email_owner,
                        text=out,
                        markdown=True)
                    per_user_store.delete_pinned_messages(comment="#/TOPOFMIND")
                targettime = m["timestamp"] + datetime.timedelta(days=1)
                per_user_store.save_pinned_message(comment='#/TOPOFMIND', timestamp=targettime)
            elif m["comment"] == '#/TODO':
                todo = pin_owner.property.todo
                if todo:
                    try:
                        todo = json.loads(todo, strict=False)
                        toplist = {}
                        for i, el in todo['list'].items():
                            toplist[int(i)] = el
                    except (TypeError, KeyError, ValueError):
                        toplist = {}
                else:
                    toplist = None
                if toplist:
                    out = "**" + todo['title'] + "**"
                    modified = pin_owner.property.todo_modified
                    if modified:
                        timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                        out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                    out += "\n\n---\n\n"
                    for i, el in sorted(toplist.items()):
                        out = out + "**" + str(i+1) + "**: " + el + "\n\n"
                    per_user_spark.post_bot_message(
                        email=email_owner,
                        text=out,
                        markdown=True)
                    per_user_store.delete_pinned_messages(comment="#/TODO")
                targettime = m["timestamp"] + datetime.timedelta(days=1)
                per_user_store.save_pinned_message(comment='#/TODO', timestamp=targettime)
            else:
                # Regular pinned reminders
                if m["id"] and len(m["id"]) > 0:
                    pin = per_user_spark.get_message(spark_id=m["id"])
                    if not pin:
                        logging.warning('Not able to retrieve message data for pinned message')
                        per_user_spark.post_bot_message(
                            email=email_owner,
                            text="You had a pinned reminder, but it was not possible to retrieve details."
                        )
                        continue
                    person = per_user_spark.get_person(spark_id=pin['personId'])
                    room = per_user_spark.get_room(spark_id=pin['roomId'])
                    if not person or not room:
                        logging.warning('Not able to retrieve person and room data for pinned message')
                        per_user_spark.post_bot_message(
                            email=email_owner,
                            text="You had a pinned reminder, but it was not possible to retrieve details."
                        )
                        continue
                    per_user_spark.post_bot_message(
                        email=email_owner,
                        text="**PIN ALERT!! - " + m["comment"] + "**\n\n" + \
                             "From " + person['displayName'] + \
                             " (" + person['emails'][0] + ")" + \
                             " in room (" + room['title'] + ")\n\n" + \
                             pin['text'] + "\n\n",
                        markdown=True)
                else:
                    per_user_spark.post_bot_message(
                        email=email_owner,
                        text="**PIN ALERT!! - " + m["comment"] + "**",
                        markdown=True)

    def validate_token(self):
        now = datetime.datetime.utcnow()
        service_status = self.spark.me.property.service_status
        if not service_status:
            self.spark.me.property.service_status = 'firehose'
        # validate_oauth_token() returns the redirect URL if token cannot be refreshed
        if len(self.spark.auth.validate_oauth_token(lazy=True)) > 0:
            if not service_status or service_status != 'invalid':
                self.spark.me.property.service_status = 'invalid'
            logging.debug("Was not able to automatically refresh token.")
            token_invalid = self.spark.me.property.token_invalid
            if not token_invalid or token_invalid != now.strftime("%Y%m%d"):
                self.spark.me.property.token_invalid = now.strftime("%Y%m%d")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Your Army Knife account has no longer access. Please type "
                         "/init in this room to re-authorize the account.")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="If you repeatedly get this error message, do /delete DELETENOW "
                         "before a new /init. This will reset your account (note: all settings as well).")
                logging.info("User (" + self.spark.me.creator + ") has invalid refresh token and got notified.")
            self.webobj.response.set_status(202, "Accepted, but not processed")
            return

    def get_autoreply_msg(self):
        if not self.spark.me.property.autoreplyMsg:
            return None

        last_auto_reply = self.spark.me.property.autoreplyMsg_last
        if last_auto_reply and last_auto_reply == self.spark.person_object.lower():
            return None
        else:
            self.spark.me.property.autoreplyMsg_last = self.spark.person_object.lower()
        return "Via " + self.spark.config.bot['email'] + " auto-reply:\n\n" + \
               self.spark.me.property.autoreplyMsg

    def message_autoreply(self):
        if self.spark.room_type == 'direct' and self.spark.person_object.lower() != self.spark.me.creator.lower():
            reply_msg = self.get_autoreply_msg()
            if not reply_msg:
                return
            app_disabled = self.spark.me.property.app_disabled
            if app_disabled and app_disabled.lower() == 'true':
                logging.debug("Account is disabled: " + self.spark.me.creator)
                return
            self.spark.enrich_data('msg')
            if not self.spark.msg_data:
                return
            if "@webex.bot" in self.spark.msg_data['text'] or \
                    "@sparkbot.io" in self.spark.msg_data['text']:
                return
            self.spark.enrich_data('person')
            self.spark.link.post_message(
                self.spark.room_id, reply_msg, markdown=True)
            if 'displayName' not in self.spark.person_data:
                display_name = "Unknown name"
            else:
                display_name = self.spark.person_data['displayName']
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="**" + display_name + " (" + self.spark.person_data['personEmail'] +
                ") sent a 1:1 message to you (auto-replied to) :**\n\n" + self.spark.msg_data['text'], markdown=True)

    def message_tracked_live(self):
        self.spark.enrich_data('account')
        self.spark.enrich_data('msg')
        self.spark.enrich_data('room')
        app_disabled = self.spark.me.property.app_disabled
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + self.spark.me.creator)
            return
        if 'title' in self.spark.room_data and 'text' in self.spark.msg_data:
            sender = self.spark.link.get_person(spark_id=self.spark.person_id)
            if 'displayName' not in sender:
                display_name = 'Unknown'
            else:
                display_name = sender['displayName']
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="**" + display_name + " (" + self.spark.person_object +
                ") in the room " + self.spark.room_data['title'] + ":**\n\n" +
                self.spark.msg_data['text'], markdown=True)       

    def message_mentions(self):
        if 'mentionedPeople' not in self.spark.data:
            return
        self.spark.enrich_data('account')
        for person in self.spark.data['mentionedPeople']:
            if person != self.spark.actor_spark_id:
                continue
            self.spark.mentioned = True
            reply_msg = self.get_autoreply_msg()
            if reply_msg:
                self.spark.link.post_message(
                    self.spark.room_id, reply_msg, markdown=True)
                reply_on = '(auto-replied to)'
            else:
                reply_on = ''
            if not self.spark.enrich_data('msg'):
                return
            if not self.spark.enrich_data('room'):
                return
            app_disabled = self.spark.me.property.app_disabled
            if app_disabled and app_disabled.lower() == 'true':
                logging.debug("Account is disabled: " + self.spark.me.creator)
                return
            if 'title' in self.spark.room_data and 'text' in self.spark.msg_data:
                no_alert = self.spark.me.property.no_mentions
                if not no_alert or no_alert.lower() != 'true':
                    mentioner = self.spark.link.get_person(spark_id=self.spark.person_id)
                    if 'displayName' not in mentioner:
                        display_name = 'Unknown'
                    else:
                        display_name = mentioner['displayName']
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="**" + display_name + " (" + self.spark.person_object +
                        ") mentioned you " + reply_on + " in the room " + self.spark.room_data['title'] + ":**\n\n" +
                        self.spark.msg_data['text'], markdown=True)

    def message_commands_to_me(self):
        if self.spark.person_object == self.spark.me.creator or \
                (self.spark.room_type != 'direct' and not self.spark.mentioned) or \
                not self.spark.enrich_data('msg') or \
                not self.spark.enrich_data('me'):
            return
        user_name = self.spark.actor_data['displayName']
        if self.spark.mentioned:
            message = self.spark.msg_data['text'][len(user_name) + 1:]
        else:
            message = self.spark.msg_data['text']
        tokens = message.split(' ')
        if tokens[0] == '/topofmind' or tokens[0] == '/tom':
            topofmind = self.spark.me.property.topofmind
            toplist = None
            if topofmind:
                try:
                    topofmind = json.loads(topofmind, strict=False)
                    toplist = topofmind['list']
                except (TypeError, KeyError, ValueError):
                    toplist = None
            if len(tokens) == 1:
                if toplist and len(toplist) > 0:
                    out = "**" + topofmind['title'] + " for " + user_name + "**"
                    modified = self.spark.me.property.topofmind_modified
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
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.person_object,
                        text="No available top of mind list",
                        markdown=True)
            elif len(tokens) == 2 and tokens[1].lower() == 'subscribe':
                # self.spark.me is now the owner of the topofmind
                # self.spark.person_object is the person wanting to subscribe
                subscriber_email = self.spark.person_object
                subscriber = actor.Actor(config=self.spark.config)
                subscriber.get_from_creator(subscriber_email)
                if not subscriber.id:
                    self.spark.link.post_bot_message(
                        email=subscriber_email,
                        text="Failed in looking up your Army Knife account. Please type /init here"
                             " and authorize Army Knife.")
                    return
                peerid = self.spark.me.id
                logging.debug("Looking for existing peer trust:(" + str(peerid) + ")")
                trust = subscriber.get_trust_relationship(peerid=peerid)
                if not trust:
                    trust = subscriber.create_reciprocal_trust(
                        url=self.spark.config.actors['myself']['factory'] + str(peerid),
                        secret=self.spark.config.new_token(),
                        desc="Top of mind subscriber",
                        relationship="associate",
                        trust_type=self.spark.config.aw_type)
                    if trust:
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Created trust relationship for top of mind subscription.")
                else:
                    self.spark.link.post_bot_message(
                        email=subscriber_email,
                        text="Trust relationship for top of mind subscription was already established.")
                if not trust:
                    self.spark.link.post_bot_message(
                        email=subscriber_email,
                        text="Creation of trust relationship for top of mind subscription failed.\n\n"
                             "Cannot create subscrition.")
                else:
                    sub = subscriber.get_subscriptions(peerid=trust['peerid'], target='properties',
                                                       subtarget='topofmind', callback=True)
                    if len(sub) > 0:
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Top of mind subscription was already created.")
                    else:
                        sub = subscriber.create_remote_subscription(peerid=trust['peerid'],
                                                                    target='properties',
                                                                    subtarget='topofmind',
                                                                    granularity='high')
                        if not sub:
                            self.spark.link.post_bot_message(
                                email=subscriber_email,
                                text="Creation of new top of mind subscription failed.")
                        else:
                            self.spark.link.post_bot_message(
                                email=subscriber_email,
                                text="Created top of mind subscription for " + self.spark.me.creator + ".")
            elif len(tokens) == 2 and tokens[1].lower() == 'unsubscribe':
                # self.spark.me is now the owner of the topofmind
                # self.spark.person_object is the person wanting to unsubscribe
                subscriber_email = self.spark.person_object
                subscriber = actor.Actor(config=self.spark.config)
                subscriber.get_from_creator(subscriber_email)
                if not subscriber.id:
                    self.spark.link.post_bot_message(
                        email=subscriber_email,
                        text="Failed in looking up your Army Knife account.")
                    return
                # My subscriptions
                subs = subscriber.get_subscriptions(
                    peerid=self.spark.me.id,
                    target='properties',
                    subtarget='topofmind',
                    callback=True)
                if len(subs) >= 1:
                    if not subscriber.delete_remote_subscription(peerid=self.spark.me.id,
                                                                 subid=subs[0]['subscriptionid']):
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Failed cancelling the top of mind subscription on your peer.")
                    elif not subscriber.delete_subscription(peerid=self.spark.me.id,
                                                            subid=subs[0]['subscriptionid']):
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Failed cancelling your top of mind subscription.")
                    else:
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Cancelled the top of mind subscription for " + self.spark.me.creator)
                # Subscriptions on me
                subs2 = subscriber.get_subscriptions(
                    peerid=self.spark.me.id,
                    target='properties',
                    subtarget='topofmind',
                    callback=False)
                if len(subs2) == 0:
                    if not subscriber.delete_reciprocal_trust(peerid=self.spark.me.id, delete_peer=True):
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Failed cancelling the trust relationship.")
                    else:
                        self.spark.link.post_bot_message(
                            email=subscriber_email,
                            text="Deleted the trust relationship.")

    def message_actions(self):
        # Ignore all messages from sparkbots
        if not self.spark.me:
            logging.debug('Dropping message where me is not set')
            return False
        if not self.spark.person_object:
            logging.debug('Warning! person_object not set, dropping...')
            return False
        logging.debug('Got message from ' + self.spark.person_object.lower())
        if "@sparkbot.io" in self.spark.person_object.lower() or \
                "@webex.bot" in self.spark.person_object.lower():
            logging.debug('Dropping webex bot message...')
            return False
        app_disabled = self.spark.me.property.app_disabled
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + self.spark.me.creator)
            return False
        # TODO Tmp disable this as invalid was set too quickly in some cases
        if self.spark.me.property.service_status == 'invalid2':
            logging.debug('Account has status invalid, dropping message')
            now = datetime.datetime.utcnow()
            token_invalid = self.spark.me.property.token_invalid
            if not token_invalid or token_invalid != now.strftime("%Y%m%d"):
                self.spark.me.property.token_invalid = now.strftime("%Y%m%d")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Your Army Knife account has no longer access. Please type "
                         "/init in this room to re-authorize the account.")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="If you repeatedly get this error message, do /delete DELETENOW "
                         "before a new /init. This will reset your account (note: all settings as well).")
                logging.info("User (" + self.spark.me.creator + ") got notified about invalid status.")
            return 
        # Send a one-time message about money support
        if not self.spark.me.property.sent_money_plea:
            self.spark.me.property.sent_money_plea = "true"
            card_cont = payments.get_subscribe_form(actor=self.spark.me, config=self.spark.config)
            self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text=payments.get_subscribe_md(actor=self.spark.me, config=self.spark.config),
                    markdown=True,
                    card=card_cont
                )
            logging.debug("User (" + self.spark.me.creator + ") got marketing message.")
        has_trial, has_subscription = payments.check_valid_trial_or_subscription(self.spark.store)
        if not has_subscription and not has_trial:
            self.spark.me.property.app_disabled = 'true'
            card_cont = payments.get_subscribe_form(actor=self.spark.me, config=self.spark.config)
            self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text=payments.get_subscribe_md(actor=self.spark.me, config=self.spark.config),
                    markdown=True,
                    card=card_cont
            )
            self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="The ArmyKnife has now been disabled to reduce the costs of operating the service. "
                         "Please consider supporting the ArmyKnife by subscribing! "
                         "(However, you may use the command `/enable` to get another 30 days.)",
                    markdown=True
            )
            # Reset the timer on trial
            self.spark.store.save_perm_attribute('first_visit', "today")
            return
        self.validate_token()
        self.global_actions()
        self.message_autoreply()
        self.message_mentions()
        self.message_commands_to_me()
        return True

    def extract_teamlist(self, team_str):
        team_list = []
        if team_str:
            if team_str[0:1] == '#':
                next_team = self.spark.link.get_memberships(spark_id=team_str[1:])
                members = []
                while next_team and 'items' in next_team:
                    members.extend(next_team['items'])
                    next_team = self.spark.link.get_memberships(get_next=True)
                for m in members:
                    team_list.append(m['personEmail'])
                if len(team_list) == 0:
                    logging.info("Not able to retrieve members for linked room in /team")
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Not able to get members of room " + team_str[1:])
                    return
            else:
                try:
                    team_list = json.loads(team_str)
                except (KeyError, TypeError, ValueError):
                    team_list = team_str
        return team_list

    def manageteam_command(self):
        if len(self.spark.msg_list) < 3 and not (len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'list'):
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text="Usage: `/manageteam add|remove|list|delete <teamname> <email(s)>` where emails are"
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
                        team = self.extract_teamlist(value)
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
        team_str = self.spark.me.property['team-' + team_name]
        team_list = self.extract_teamlist(team_str)
        out = ''
        if len(team_list) == 0 and team_cmd == 'list':
            out = "The team does not exist."
        elif team_cmd == 'list':
            out = "**Team members of team " + team_name + "**\n\n"
            for t in team_list:
                out += t + "\n\n"
            team_list = []
        elif team_cmd == 'delete':
            if len(self.spark.msg_list) > 3:
                out += "Use remove to remove an email address from a team. Delete is to delete an entire team!\n\n"
            else:
                out += "Deleted team " + team_name + "\n\n"
                self.spark.me.property['team-' + team_name] = None
            team_list = []
        elif team_str and team_str[0:1] == '#':
            out += "This team is linked to a room, so only /manageteam list and delete commands are allowed."
            team_list = []
        elif team_cmd == 'add':
            for e in emails:
                out += "Added " + e + "\n\n"
                team_list.append(str(e.strip()))
        elif team_cmd == 'init':
            for e in emails:
                out += "Added " + e + "\n\n"
                team_list.append(str(e))
        elif team_cmd == 'remove':
            for e in emails:
                for e2 in team_list:
                    if e == e2:
                        team_list.remove(str(e.strip()))
                        out += "Removed " + e + "\n\n"
        if len(team_list) > 0:
            self.spark.me.property['team-' + team_name] = json.dumps(team_list)
        if len(out) > 0:
            self.spark.link.post_bot_message(
                email=self.spark.person_object,
                text=out,
                markdown=True)

    def team_command(self):
        self.spark.link.delete_message(self.spark.object_id)
        if len(self.spark.msg_list) != 3:
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Usage: `/team link|init|add|remove|verify|sync team_name`", markdown=True)
            return
        team_cmd = self.spark.msg_list[1]
        team_name = self.spark.msg_list[2]
        team_str = self.spark.me.property['team-' + team_name]
        team_list = self.extract_teamlist(team_str)
        if not self.spark.enrich_data('room'):
            return
        if self.spark.room_data and 'title' in self.spark.room_data:
            title = self.spark.room_data['title']
        else:
            title = 'Unknown'
        out = ''
        next_members = self.spark.link.get_memberships(spark_id=self.spark.room_id)
        members = []
        while next_members and 'items' in next_members:
            members.extend(next_members['items'])
            next_members = self.spark.link.get_memberships(get_next=True)
        if len(members) == 0:
            logging.info("Not able to retrieve members for room in /team")
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Not able to get members of room.")
            return
        if team_cmd == 'init':
            team_list = []
            out = "**Initializing team " + team_name + " with members from room " + title + "**\n\n"
            for m in members:
                out += "Added " + m['personEmail'] + "\n\n"
                team_list.append(str(m['personEmail']))
            if len(team_list) > 0:
                self.spark.me.property['team-' + team_name] = json.dumps(team_list)
        elif team_cmd == 'link':
            if 'id' in self.spark.room_data:
                self.spark.me.property['team-' + team_name] = '#' + self.spark.room_id
                out = "**Linked team " + team_name + " to members of room " + title + "**\n\n"
            else:
                out = "Error in getting room data.\n\n"
        elif team_cmd == 'add' or team_cmd == 'remove' or team_cmd == 'verify' or team_cmd == 'sync':
            if len(team_list) == 0:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="You tried to use /team with a non-existent team. Did you mean team init?")
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
                for m in members:
                    try:
                        team_list.remove(m['personEmail'])
                        if team_cmd == 'remove':
                            self.spark.link.delete_member(spark_id=m['id'])
                            out += "Removed from room: " + m['personEmail'] + "\n\n"
                    except ValueError:
                        if team_cmd == 'verify':
                            out += "In room, but not in team: " + m['personEmail'] + "\n\n"
                        elif team_cmd == 'sync':
                            out += "Removed from room: " + m['personEmail'] + "\n\n"
                            self.spark.link.delete_member(spark_id=m['id'])
                for e in team_list:
                    if team_cmd == 'add' or team_cmd == 'sync':
                        self.spark.link.add_member(spark_id=self.spark.room_id, email=e)
                        out += "Added to room: " + e + "\n\n"
                    elif team_cmd == 'verify':
                        out += "Not in room, but in team: " + e + "\n\n"
        self.spark.link.post_bot_message(
            email=self.spark.me.creator,
            text=out,
            markdown=True)

    def memberships_created(self):
        app_disabled = self.spark.me.property.app_disabled
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + self.spark.me.creator)
            return
        if not self.spark.enrich_data('room'):
            return
        if self.spark.person_object == self.spark.me.creator:
            if 'title' in self.spark.room_data:
                no_alert = self.spark.me.property.no_newrooms
                if not no_alert or no_alert.lower() != 'true':
                    self.spark.link.post_bot_message(email=self.spark.me.creator,
                                                     text="You were added to the room " + self.spark.room_data['title'])
        room = self.spark.store.load_room(self.spark.room_id)
        if room and "boxFolderId" in room:
            box = self.spark.me.get_peer_trustee(shorttype='boxbasic')
            proxy = aw_proxy.AwProxy(peer_target=box, config=self.spark.config)
            params = {}
            if self.spark.body['event'] == 'created':
                params = {
                    'collaborations': [
                        {
                            'email': self.spark.person_object,
                        },
                    ],
                }
            elif self.spark.body['event'] == 'deleted':
                params = {
                    'collaborations': [
                        {
                            'email': self.spark.person_object,
                            'action': 'delete',
                        },
                    ],
                }
            proxy.change_resource(path='resources/folders/' + room["boxFolderId"], params=params)
            if proxy.last_response_code < 200 or proxy.last_response_code > 299:
                logging.warning('Unable to add/remove collaborator(' + self.spark.person_object +
                                ') to Box folder(' + room["boxFolderId"] + ')')
            else:
                logging.debug('Added/removed collaborator(' + self.spark.person_object +
                              ') to Box folder(' + room["boxFolderId"] + ')')

    def bot_room_commands(self):
        if self.spark.cmd == '/me':
            me_data = self.spark.link.get_me()
            if not me_data:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Not able to retrieve data from Cisco Webex Teams, you may need to do /init.",
                    markdown=True)
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Your Cisco Webex Teams Account**  \n----  \n" +
                         "**Cisco Webex Teams nickname**: " + me_data['nickName'] + "  \n"
                         "**Cisco Webex Teams id**: " + me_data['id'] + "  \n"
                         "**Cisco Webex Teams avatar**: " + (me_data['avatar'] or '') + "  \n"
                         "Your account is enabled and fully functioning!",
                    markdown=True)
        elif self.spark.cmd == '/listwebhooks':
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="**All Registered Webhooks on Your Account**  \n---",
                markdown=True)
            ret = self.spark.link.get_all_webhooks()
            while 1:
                if not ret:
                    break
                for h in ret['webhooks']:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="**Name(id)**: " + h['name'] + " (" + h['id'] + ")"
                             "\n\n**Events**: " + h['resource'] + ":" +
                             h['event'] +
                             "\n\n**Target**: " + h['targetUrl'] +
                             "\n\n**Created**: " + h.get('created','-') +
                             "\n\n- - -\n\n",
                        markdown=True
                    )
                if not ret['next']:
                    break
                ret = self.spark.link.get_all_webhooks(uri=ret['next'])
        elif self.spark.cmd == '/deletewebhook':
            if len(self.spark.msg_list) != 2:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage `/deletewebook <webhookid>`.\n\nUse /listwebhooks to get the id."
                )
            else:
                hook_id = self.spark.msg_list_wcap[1]
                ret = self.spark.link.unregister_webhook(spark_id=hook_id)
                if ret is not None:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Deleted webhook: " + hook_id
                    )
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Was not able to delete webhook: " + hook_id
                    )
        elif self.spark.cmd == '/cleanwebhooks':
            self.spark.me.property.firehoseId = None
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Started cleaning up ALL webhooks...")
            self.spark.link.clean_all_webhooks(spark_id=self.spark.room_id)
            msghash = hashlib.sha256()
            msghash.update(self.spark.me.passphrase.encode('utf-8'))
            hook = self.spark.link.register_webhook(
                name='Firehose',
                target=self.spark.config.root + self.spark.me.id + '/callbacks/firehose',
                resource='all',
                event='all',
                secret=msghash.hexdigest()
                )
            if hook and hook['id']:
                logging.debug('Successfully registered messages firehose webhook')
                self.spark.me.property.firehoseId = hook['id']
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Successfully created new Army Knife webhook.")
        elif self.spark.cmd == '/manageteam':
            self.manageteam_command()
            return
        elif self.spark.cmd == '/countrooms':
            out = "**Counting rooms...**\n\n----\n\n"
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text=out,
                markdown=True)
            out = ""
            next_rooms = self.spark.link.get_rooms()
            rooms = []
            while next_rooms and 'items' in next_rooms:
                rooms.extend(next_rooms['items'])
                next_rooms = self.spark.link.get_rooms(get_next=True)
            if len(rooms) > 0:
                out += "**You are member of " + str(len(rooms)) + " group rooms.**\n\n"
            else:
                out += "**No rooms found.**"
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text=out,
                markdown=True)
        elif self.spark.cmd == '/checkmember':
            if len(self.spark.msg_list) == 1:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: `/checkmember <email>` to check room memberships for the email",
                    markdown=True)
                return
            if not fargate.in_fargate() and not fargate.fargate_disabled():
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="You requested a tough task! I will call upon one of my workers to check memberships...",
                    markdown=True)
                fargate.fork_container(self.webobj.request, self.spark.actor_id)
            else:
                target = self.spark.msg_list[1]
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Room memberships for " + target + "**\n\n----\n\n",
                    markdown=True)
                self.check_member(target)
        elif self.spark.cmd == '/deletemember':
            if len(self.spark.msg_list) < 3:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: `/deletemember <email> <room-id>` to delete user with <email>"
                         " from a room with <room-id>.\n\n"
                         " or: `/deletemember <email> FORCE count` to delete user with <email>"
                         " from ALL shared room where count=number of shared rooms (use /checkmember).",
                    markdown=True)
                return
            target = self.spark.msg_list[1]
            ids = []
            if self.spark.msg_list_wcap[2] == "FORCE":
                if len(self.spark.msg_list) < 4:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Usage: `/deletemember <email> <room-id>` to delete user with <email>"
                             " from a room with <room-id>.\n\n"
                             " or: `/deletemember <email> FORCE count` to delete user with <email>"
                             " from ALL shared rooms, where count=number of shared rooms (use /checkmember).",
                        markdown=True)
                    return
                if not fargate.in_fargate() and not fargate.fargate_disabled():
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="You requested a tough task! I will call upon one of my workers to delete memberships...",
                        markdown=True)
                    fargate.fork_container(self.webobj.request, self.spark.actor_id)
                    return
                count = -1
                try:
                    target_count = int(self.spark.msg_list[3])
                except TypeError:
                    target_count = 0
                if target_count > 0:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Checking number of memberships (please be patient)...",
                        markdown=True)
                    count, ids = self.check_member(target, quiet=True)
                if count != target_count:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Count does not match number of rooms (" + str(count) + ").",
                        markdown=True)
                    return
            else:
                ids = self.spark.msg_data['text'][len(self.spark.msg_list[0]) +
                                                  len(self.spark.msg_list[1]) +
                                                  2:].replace(" ", "").split(',')
            ok_out = ""
            failed_out = ""
            for i in ids:
                next_members = self.spark.link.get_memberships(spark_id=str(i))
                members = []
                while next_members and 'items' in next_members:
                    members.extend(next_members['items'])
                    next_members = self.spark.link.get_memberships(get_next=True)
                for m in members:
                    if m['personEmail'].lower() == target:
                        res = self.spark.link.delete_member(spark_id=m['id'])
                        if res is not None:
                            if len(ok_out) > 0:
                                ok_out += ","
                            ok_out += str(i)
                        else:
                            if len(failed_out) > 0:
                                failed_out += ","
                            failed_out += str(i)
            if len(ok_out) > 0:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text=target + " was deleted from (can be used in `/addmember` to add them back): " + ok_out,
                    markdown=True)
            if len(failed_out) > 0:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text=target + " was NOT deleted from " + failed_out,
                    markdown=True)
        elif self.spark.cmd == '/addmember':
            if len(self.spark.msg_list) < 3:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: `/addmember <email> <room-id>` to add user with <email> to a room with <room-id>.",
                    markdown=True)
                return
            ids = self.spark.msg_data['text'][len(self.spark.msg_list[0]) +
                                              len(self.spark.msg_list[1]) +
                                              2:].replace(" ", "").split(',')
            logging.debug(str(self.spark.msg_list_wcap))
            for i in ids:
                res = self.spark.link.add_member(spark_id=i, email=self.spark.msg_list[1])
                if res:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Added " + self.spark.msg_list[1] + " to the room " + i,
                        markdown=True)
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Failed adding " + self.spark.msg_list[1] + " to room " + i,
                        markdown=True)
        elif self.spark.cmd == '/get':
            if len(self.spark.msg_list) == 1:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: `/get <all|nickname>` to get messages from all or from a special nickname.",
                    markdown=True)
                return
            if len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'all':
                trackers = self.spark.store.load_trackers()
                nicknames = []
                for tracker in trackers:
                    nicknames.append(tracker["nickname"])
            else:
                nicknames = [self.spark.msg_list[1]]
            for nick in nicknames:
                msgs = self.spark.store.load_messages(nickname=nick)
                if not msgs:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text='**No messages from ' +
                             nick + '**', markdown=True)
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text='-------- -------- --------- --------- ---------')
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text='**Messages from: ' +
                             nick + '**', markdown=True)
                    for msg in msgs:
                        msg_content = self.spark.link.get_message(msg["id"])
                        if not msg_content:
                            continue
                        text = msg_content['text']
                        room = self.spark.link.get_room(msg["roomId"])
                        self.spark.link.post_bot_message(
                            email=self.spark.me.creator,
                            text=msg["timestamp"].strftime('%c') + ' - (' + room['title'] + ')' + '\r\n' + text)
                    self.spark.store.clear_messages(nickname=nick)
        elif self.spark.cmd == '/pins':
            msgs = self.spark.store.get_pinned_messages()
            if msgs:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Your Pinned Reminders (all times are in UTC)**\n\n----\n\n",
                    markdown=True)
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**You have no Pinned Reminders**",
                    markdown=True)
            for m in msgs:
                if len(m["id"]) == 0:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="**" + m["timestamp"].strftime('%Y-%m-%d %H:%M') + "** -- " + m[
                            "comment"] + "\n\n----\n\n",
                        markdown=True)
                    continue
                pin = self.spark.link.get_message(spark_id=m["id"])
                if not pin:
                    logging.warning('Not able to retrieve message data for pinned message ')
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Not possible to retrieve pinned message details."
                    )
                    continue
                person = self.spark.link.get_person(spark_id=pin['personId'])
                room = self.spark.link.get_room(spark_id=pin['roomId'])
                if not person or not room:
                    logging.warning('Not able to retrieve person and room data for pinned message')
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Not possible to retrieve pinned message person and room details."
                    )
                    continue
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**" + m["timestamp"].strftime('%Y-%m-%d %H:%M') + "** -- " + m["comment"] + "\n\nFrom " +
                         person['displayName'] + " (" + person['emails'][0] + ")" + " in room (" + room[
                             'title'] + ")\n\n" +
                         pin['text'] + "\n\n----\n\n",
                    markdown=True)
        elif self.spark.cmd == '/box':
            box = self.spark.me.get_peer_trustee(shorttype='boxbasic')
            if not box:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Failed to create new box service.")
                return
            if len(self.spark.msg_list) > 1:
                box_root_id = self.spark.me.property.boxRootId
                if box_root_id:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="You have created the Box root folder in Box and started to use it. "
                             "You must do /nobox before you can change root folder.")
                    return
                box_root = self.spark.msg_list_wcap[1]
            else:
                box_root = self.spark.me.property.boxRoot
                if not box_root:
                    box_root = 'WebexTeamsRoomFolders'
            self.spark.me.property.boxRoot = box_root
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Your box service is available and can be authorized at " + box['baseuri'] +
                     "/www\n\n" +
                     "Then use /boxfolder in group rooms to create new Box folders (created below the " +
                     box_root + " folder).")
        elif self.spark.cmd == '/nobox':
            if not self.spark.me.delete_peer_trustee(shorttype='boxbasic'):
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Failed to delete box service.")
            else:
                self.spark.me.property.boxRoot = None
                self.spark.me.propertyboxRootId = None
                box_rooms = self.spark.store.load_rooms()
                for b in box_rooms:
                    self.spark.store.delete_from_room(b.id, boxfolder=True)
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Deleted your box service.")
        elif self.spark.cmd == '/app':
            if len(self.spark.msg_list) > 1:
                apptype = self.spark.msg_list[1]
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: /app <apptype>, e.g. /app googlemail")
                return
            app = self.spark.me.get_peer_trustee(shorttype=apptype)
            sub = self.spark.me.create_remote_subscription(
                peerid=app['peerid'],
                target='properties',
                subtarget='new',
                granularity='high')
            if sub:
                logging.debug('Created a new subscription at ' + sub)
            if not app or not sub:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Failed to create new application of type " + apptype + '.')
                return
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Your app is available and can be authorized at " + app['baseuri'] +
                     "/www\n\n" +
                     "Then use /appconfig to configure it.")
        elif self.spark.cmd == '/noapp':
            if len(self.spark.msg_list) > 1:
                apptype = self.spark.msg_list[1]
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: /noapp <apptype>, e.g. /noapp googlemail")
                return
            if not self.spark.me.delete_peer_trustee(shorttype=apptype):
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Failed to delete " + apptype + " service.")
            else:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Deleted your " + apptype + " service.")

    def all_rooms_commands(self):
        if self.spark.cmd == '/pin':
            self.spark.link.delete_message(self.spark.data['id'])
            if len(self.spark.msg_list) >= 2:
                try:
                    nr = int(self.spark.msg_list[1]) - 1
                except (ValueError, TypeError, KeyError):
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Usage: `/pin x +a[m|h|d|w] Your message` (x and a must be digits).\n\n"
                             "**Using 1 for x.**",
                        markdown=True)
                    nr = 0
                if nr < 0:
                    # Typed in 0 means no message
                    nr = None
            else:
                nr = 0
            max_back = 10
            if nr and nr > 10:
                max_back = nr + 1
            targettime = None
            comment = None
            if len(self.spark.msg_list) > 2:
                if len(self.spark.msg_list) > 3:
                    comment = self.spark.msg_data['text'][
                              len(self.spark.msg_list[0]) +
                              len(self.spark.msg_list[1]) +
                              len(self.spark.msg_list[2]) + 3:]
                if '+' in self.spark.msg_list[2]:
                    deltalist = re.split('[mhdw]', self.spark.msg_list[2][1:])
                    if deltalist:
                        delta = int(deltalist[0])
                    else:
                        delta = 1
                    typelist = re.split('\d+', self.spark.msg_list[2])
                    if deltalist and len(deltalist) == 2:
                        deltatype = typelist[1]
                    else:
                        deltatype = 'd'
                else:
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="Usage: `/pin x +a[m|h|d|w] Your message`, e.g. /pin 3 +2h, where"
                             " m = minutes, h = hours, d = days, w = weeks"
                             "       Use x=0 to set a reminder with no reference to a message, e.g."
                             " `/pin 0 +2h Time to leave!`",
                        markdown=True)
                    return
                now = datetime.datetime.utcnow()
                if deltatype == 'm':
                    targettime = now + datetime.timedelta(minutes=delta)
                elif deltatype == 'h':
                    targettime = now + datetime.timedelta(hours=delta)
                elif deltatype == 'w':
                    targettime = now + datetime.timedelta(days=(delta * 7))
                else:
                    targettime = now + datetime.timedelta(days=delta)
            msgs = None
            if nr is not None:
                msgs = self.spark.link.get_messages(
                    spark_id=self.spark.room_id,
                    before_id=self.spark.data['id'],
                    max_msgs=max_back)
            if targettime:
                if nr is not None:
                    self.spark.store.save_pinned_message(msg_id=msgs[nr]['id'], comment=comment, timestamp=targettime)
                else:
                    self.spark.store.save_pinned_message(comment=comment, timestamp=targettime)
            elif nr is not None:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Pinned (" + msgs[nr]['created'] + ") from " +
                         msgs[nr]['personEmail'] + ":** " + msgs[nr]['text'],
                    markdown=True)
        elif self.spark.cmd == '/todo' or self.spark.cmd == '/followup' or self.spark.cmd == '/fu':
            self.spark.link.delete_message(self.spark.data['id'])
            if len(self.spark.msg_list) > 1:
                try:
                    nr = int(self.spark.msg_list[1]) - 1
                except (ValueError, TypeError, KeyError):
                    nr = 0
            else:
                nr = 0
            if nr > 10:
                max_back = nr + 1
            else:
                max_back = 10
            msgs = self.spark.link.get_messages(
                spark_id=self.spark.room_id,
                before_id=self.spark.data['id'],
                max_msgs=max_back)
            if not msgs:
                return
            msg_data = self.spark.link.get_message(msgs[nr]['id'])
            if 'text' in msg_data:
                listitem = msg_data['text']
            else:
                listitem = "FAILED MSG RETRIEVAL"
            todo = self.spark.me.property.todo
            if todo:
                try:
                    todo = json.loads(todo, strict=False)
                    toplist = {}
                    for i, el in todo['list'].items():
                        toplist[int(i)] = el
                except (TypeError, KeyError, ValueError):
                    toplist = {}
            else:
                toplist = {}
                todo = {'email': self.spark.me.creator, 'displayName': self.spark.me.property.displayName,
                        'title': "Todo List"}
                if self.spark.cmd == '/followup' or self.spark.cmd == '/fu':
                    todo['title'] = "FollowUp List"
            index = len(toplist)
            toplist[index] = listitem
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Added list item **" + str(index + 1) + "** with text `" + toplist[index] + "`",
                markdown=True)
            todo['list'] = toplist
            out = json.dumps(todo, sort_keys=True, ensure_ascii=False)
            self.spark.me.property.todo = out
            now = datetime.datetime.now()
            self.spark.me.property.todo_modified = now.strftime('%Y-%m-%d %H:%M')
        elif self.spark.cmd == '/makepublic':
            uuid = self.spark.store.add_uuid_to_room(self.spark.room_id)
            if not uuid:
                self.spark.link.post_message(
                    id=self.spark.room_id,
                    text="Failed to make room public.")
            else:
                self.spark.link.post_message(
                    spark_id=self.spark.room_id, text="Public URI: " + self.spark.config.root +
                    self.spark.me.id + '/callbacks/joinroom?id=' + uuid)
        elif self.spark.cmd == '/makeprivate':
            if not self.spark.store.delete_from_room(self.spark.room_id, del_uuid=True):
                self.spark.link.post_message(
                    spark_id=self.spark.room_id,
                    text="Failed to make room private.")
            else:
                self.spark.link.post_message(
                    spark_id=self.spark.room_id,
                    text="Made room private and add URL will not work anymore.")
        elif self.spark.cmd == '/listroom':
            self.spark.link.delete_message(self.spark.object_id)
            if not self.spark.enrich_data('room'):
                return
            msg = ''
            for key in self.spark.room_data:
                msg = msg + "**" + str(key) + "**: " + str(self.spark.room_data[key]) + "\n\n"
                if key == 'id':
                    id2 = base64.b64decode(self.spark.room_data[key].encode('utf-8')).decode('utf-8').split("ROOM/")
                    if len(id2) >= 2:
                        msg = msg + "**Web URL**:" + " https://web.ciscospark.com/rooms/" + id2[1] + "\n\n"
            if len(msg) > 0:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Room Details**\n\n" + msg +
                         "\n\nUse `/listmembers` and `/listfiles` to get other room details.",
                    markdown=True)
        elif self.spark.cmd == '/listfiles':
            self.spark.link.delete_message(self.spark.data['id'])
            feature_toggles = self.spark.me.property.featureToggles
            msgs = self.spark.link.get_messages(spark_id=self.spark.room_id, max_msgs=200)
            if not self.spark.enrich_data('room'):
                return
            if 'title' in self.spark.room_data:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="**Files in room: " + self.spark.room_data['title'] + "**\n\n",
                    markdown=True)
            while msgs:
                for msg in msgs:
                    if 'files' in msg:
                        for f in msg['files']:
                            details = self.spark.link.get_attachment_details(f)
                            if 'content-disposition' in details:
                                filename = re.search(r"filename[^;\n=]*=(['\"])*(?:utf-8\'\')?(.*)(?(1)\1|)",
                                                     details['content-disposition']).group(2)
                            else:
                                filename = 'unknown'
                            timestamp = datetime.datetime.strptime(msg['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
                            time = timestamp.strftime('%Y-%m-%d %H:%M')
                            if 'content-length' in details:
                                size = int(details['content-length']) / 1024
                            else:
                                size = 'x'
                            if feature_toggles and (
                                    'listfiles' in feature_toggles or 'beta' in feature_toggles):
                                self.spark.link.post_bot_message(
                                    email=self.spark.me.creator,
                                    text=time + ": [" + filename + " (" + str(size) + " KB)](" +
                                    self.spark.config.root +
                                    self.spark.me.id + '/www/getattachment?url=' + f + "&filename=" + filename + ")",
                                    markdown=True)
                            else:
                                self.spark.link.post_bot_message(
                                    email=self.spark.me.creator,
                                    text=time + ": " + filename + " (" + str(size) + " KB)",
                                    markdown=True)
                # Using max=0 gives us the next batch
                msgs = self.spark.link.get_messages(spark_id=self.spark.room_id, max_msgs=0)
        elif self.spark.cmd == '/listmembers':
            self.spark.link.delete_message(self.spark.data['id'])
            if len(self.spark.msg_list) == 2 and self.spark.msg_list[1] == 'csv':
                csv = True
            else:
                csv = False
            next_members = self.spark.link.get_memberships(spark_id=self.spark.room_id)
            members = []
            while next_members and 'items' in next_members:
                members.extend(next_members['items'])
                next_members = self.spark.link.get_memberships(get_next=True)
            if len(members) == 0:
                logging.info("Not able to retrieve members for room in /listmembers")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Not able to retrieve members in room to list members.")
                return
            memberlist = ""
            sep = ""
            for m in members:
                if csv:
                    memberlist = memberlist + sep + m['personEmail']
                    sep = ","
                else:
                    memberlist = memberlist + "\n\n" + m['personDisplayName'] + " (" + m['personEmail'] + ")"
            if not self.spark.enrich_data('room'):
                return
            if 'title' in self.spark.room_data:
                memberlist = "**Members in room: " + self.spark.room_data['title'] + "**\n\n----\n\n" + memberlist
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text=memberlist, markdown=True)
        elif self.spark.cmd == '/team':
            self.team_command()
            return
        elif self.spark.cmd == '/copyroom':
            # Only allow copyroom in group rooms
            if self.spark.room_type == 'direct':
                return
            self.spark.link.delete_message(self.spark.object_id)
            if len(self.spark.msg_list) == 1:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Usage: `/copyroom New Room Title`", markdown=True)
                return
            next_members = self.spark.link.get_memberships(spark_id=self.spark.room_id)
            members = []
            while next_members and 'items' in next_members:
                members.extend(next_members['items'])
                next_members = self.spark.link.get_memberships(get_next=True)
            if len(members) == 0:
                logging.info("Not able to retrieve members for room in /copyroom")
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Not able to retrieve room members.")
                return
            if len(members) > 25:
                if not fargate.in_fargate() and not fargate.fargate_disabled():
                    self.spark.link.post_bot_message(
                        email=self.spark.me.creator,
                        text="You requested a tough task! I will call upon one of my workers to add members...",
                        markdown=True)
                    fargate.fork_container(self.webobj.request, self.spark.actor_id)
                    return
            title = self.spark.msg_data['text'][len(self.spark.msg_list[0]) + 1:]
            room_data = self.spark.link.get_room(spark_id=self.spark.room_id)
            if room_data and 'teamId' in room_data:
                team_id = room_data['teamId']
            else:
                team_id = None
            room = self.spark.link.create_room(title, team_id)
            if not room:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="Not able to create new room.")
                return
            for m in members:
                self.spark.link.add_member(spark_id=room['id'], person_id=m['personId'])
            self.spark.link.post_bot_message(
                email=self.spark.me.creator,
                text="Created new room and added the same members as in that room.")
        elif self.spark.cmd == '/boxfolder':
            # box_root is set when issueing the /box command
            box_root = self.spark.me.property.boxRoot
            if not box_root or len(box_root) == 0:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text="You have not authorized the Box service. Go to the 1:1 bot room and do"
                         " the /box command first.")
                return
            box = self.spark.me.get_peer_trustee(shorttype='boxbasic')
            proxy = aw_proxy.AwProxy(peer_target=box, config=self.spark.config)
            # box_root_id is set the first time a /boxfolder command is run
            box_root_id = self.spark.me.property.boxRootId
            if not box_root_id:
                # Create the root folder
                params = {
                    'name': box_root,
                }
                root_folder = proxy.create_resource(
                    path='/resources/folders',
                    params=params)
                if root_folder and 'id' in root_folder:
                    box_root_id = root_folder['id']
                    self.spark.me.property.boxRootId = box_root_id
                else:
                    if 'error' in root_folder and root_folder['error']['code'] == 401:
                        self.spark.link.post_bot_message(
                            email=self.spark.me.creator,
                            text="You need to authorize the Box service first. Do /box from the 1:1 bot room.")
                    elif 'error' in root_folder and root_folder['error']['code'] == 409:
                        self.spark.link.post_bot_message(
                            email=self.spark.me.creator,
                            text="The root folder " + box_root +
                                 " already exists in Box. Delete it, or choose a different name"
                                 " root folder (/nobox, then /box anothername)")
                    elif 'error' in root_folder and root_folder['error']['code'] != 401:
                        self.spark.link.post_bot_message(
                            email=self.spark.me.creator,
                            text="Failed to create the Box root folder (" + root_folder['error']['message'] + ")")
                    else:
                        self.spark.link.post_bot_message(
                            email=self.spark.me.creator,
                            text="Unknown error trying to create Box root folder.")
                    return
            room = self.spark.store.load_room(self.spark.room_id)
            if room and len(room.get("boxFolderId", '')) > 0:
                folder = proxy.get_resource('resources/folders/' + room["boxFolderId"])
                if folder and 'url' in folder:
                    self.spark.link.post_message(
                        spark_id=self.spark.room_id,
                        text='The box folder name for this room is **' +
                             folder['name'] + '**, and can be found at: ' +
                             folder['url'], markdown=True)
                else:
                    self.spark.link.post_message(
                        spark_id=self.spark.room_id,
                        text="Unable to retrieve shared link from Box for this room's folder")
                return
            # /boxfolder <rootfoldername>
            if len(self.spark.msg_list) > 1:
                folder_name = self.spark.msg_list_wcap[1]
            else:
                room = self.spark.link.get_room(self.spark.room_id)
                folder_name = room['title']
            params = {
                'name': folder_name,
                'parent': box_root_id,
            }
            emails = self.spark.link.get_memberships(spark_id=self.spark.room_id)
            # Create the params['email'] list
            if emails and emails['items']:
                params['emails'] = []
                for item in emails['items']:
                    if item['isMonitor'] or item['personEmail'] == self.spark.me.creator:
                        continue
                    params['emails'].append(item['personEmail'])
            folder = proxy.create_resource(
                path='/resources/folders',
                params=params)
            if folder and 'url' in folder:
                url = folder['url']
            else:
                url = 'No shared link available'
            if folder and 'id' in folder and 'error' not in folder:
                self.spark.me.create_remote_subscription(
                    peerid=box['peerid'],
                    target='resources',
                    subtarget='folders',
                    resource=folder['id'],
                    granularity='high')
                self.spark.link.post_message(
                    spark_id=self.spark.room_id,
                    text="Created a new box folder for this room with name: " + folder_name +
                         " and shared link: " + url + ". Also added all room members as editors.")
                self.spark.store.add_to_room(room_id=self.spark.room_id, box_folder_id=folder['id'])
            else:
                if folder and 'error' in folder:
                    if 'url' in folder:
                        self.spark.link.post_message(
                            spark_id=self.spark.room_id,
                            text='The box folder for this room can be found at: ' + folder['url'])
                    else:
                        self.spark.link.post_message(
                            spark_id=self.spark.room_id,
                            text=folder['error']['message'])
                else:
                    self.spark.link.post_message(
                        spark_id=self.spark.room_id,
                        text='Failed to create new folder for unknown reason.')
        elif self.spark.cmd == '/noboxfolder':
            room = self.spark.store.load_room(self.spark.room_id)
            if not room:
                self.spark.link.post_message(
                    spark_id=self.spark.room_id,
                    text="You don't have a box folder for this room. Do /boxfolder [foldername] to"
                         " create one. \n\nDefault folder name is the room name.")
            else:
                box = self.spark.me.get_peer_trustee(shorttype='boxbasic')
                proxy = aw_proxy.AwProxy(peer_target=box, config=self.spark.config)
                if "boxFolderId" in room and not proxy.delete_resource('resources/folders/' + room["boxFolderId"]):
                    self.spark.link.post_message(
                        spark_id=self.spark.room_id,
                        text="Failed to disconnect the Box folder from this room.")
                else:
                    self.spark.store.delete_from_room(room_id=self.spark.room_id, del_boxfolder=True)
                    self.spark.link.post_message(
                        spark_id=self.spark.room_id,
                        text="Disconnected the Box folder from this room. The Box folder was not deleted.")

    def messages_created(self):
        app_disabled = self.spark.me.property.app_disabled
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + self.spark.me.creator)
            return
        if self.spark.room_id == self.spark.config.bot["admin_room"]:
            logging.debug("Integration firehose in admin room, dropping...")
            return
        live_trackers = False if self.spark.me.property.live_trackers == 'false' else True
        # will not store message, but return True if message is tracked
        tracked = self.spark.store.process_message(self.spark.data, not live_trackers)
        if tracked and live_trackers:
            self.message_tracked_live()
        if self.spark.person_id != self.spark.actor_spark_id:
            # We only execute commands in messages from the Cisco Webex Teams user attached
            # to this ArmyKnife actor (not to).
            return
        if self.spark.cmd[0:1] != '/':
            return
        # If the command was run in the bot room, it was already counted there
        if self.spark.room_id != self.spark.chat_room_id:
            self.spark.store.stats_incr_command(self.spark.cmd)
        if not self.spark.service_status or \
                self.spark.service_status == 'invalid' or \
                self.spark.service_status == 'firehose':
            self.spark.me.property.service_status = 'active'
        if self.spark.cmd == '/fargate':
            fargate.fork_container(self.webobj.request, self.spark.actor_id)
            return
        """
        Apr 11, 2020, GTW, disabled as we now don't enforce subscriptions
        # Global beta users bypass subscriptions and trials!
        feature_toggles = self.spark.me.property.featureToggles
        if not feature_toggles or 'beta' not in feature_toggles:
            abort, msg = payments.check_subscriptions(self.spark.cmd, self.spark.store, 'integration')
            if msg:
                self.spark.link.post_bot_message(
                    email=self.spark.me.creator,
                    text=msg,
                    markdown=True)
            if abort:
                return """
        if self.spark.room_id == self.spark.chat_room_id:
            # Commands run in the 1:1 bot room that need OAuth rights on behalf
            # of the user to execute
            self.bot_room_commands()
        if self.spark.room_id != self.spark.chat_room_id:
            self.all_rooms_commands()
        return
