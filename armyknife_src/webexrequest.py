import json
import logging
import hmac
import hashlib
import datetime
from actingweb import actor
from . import ciscowebexteams
from . import armyknife
from . import fargate


class WebexTeamsRequest:
    """ Keeper of data from a request from Army Knife (bot or webhook)

        For use outside the object:
        ------
         auth: the actingweb auth object
         actor_id: the current actor id
         actor_spark_id: the Army Knife id of the actor
         actor_data: Personal info on the Army Knife user
         object_id: Army Knife id of the object that this request is about
         room_id: Id of the current room
         is_actor_user: is the actor a valid user (True after successful re_init)
         person_id: the Army Knife id of the person acting in this message
         is_actor_bot: is the bot the actor/person here (True if email of person_id is the bot email)
         person_object: the email of the person being acted upon (or None)
         is_bot_object: is the person acted upon the bot?
         person_data: If enriched, the Army Knife data for this person
         room_type: The type of room ("direct", "group")
         room_data: If enriched, the Army Knife data of the room
         msg_data: If enriched, the Army Knife data of the message
         me: The actor object if an actor was found and associated with the acting person
         mentioned: True if this message mentioned the user
         link: for communicating with Army Knife on behalf of this actor
         store: for storing data on this actor
         data: the "data" dict from the message received
         body: dict of the entire body (including "data")
         msg_list_wcap: List of words from the message with caps
         msg_list: List of words from the message, all lower case
         chat_room_id: This user's 1:1 room with the bot
         cmd: The command (/cmd)
    NOTE!!! that actor and object is the same person for messages, created events
    """
    def __init__(self, body=None, auth=None, myself=None, config=None):
        self.auth = auth
        if not auth:
            self.bot_request = True
        else:
            self.bot_request = False
        self.__signature_header = 'X-Spark-Signature'
        self.config = config
        self.__rawbody = None
        self.me = myself
        if myself:
            self.actor_id = myself.id
        else:
            self.actor_id = None
        self.actor_spark_id = None
        self.link = ciscowebexteams.CiscoWebexTeams(auth=self.auth, actor_id=self.actor_id, config=self.config)
        self.store = armyknife.ArmyKnife(actor_id=self.actor_id, config=self.config)
        self.data = None
        self.person_id = None
        self.person_object = None
        self.person_data = None
        self.room_type = None
        self.room_id = None
        self.room_data = None
        self.msg_data = None
        self.object_id = None
        self.is_actor_user = False
        self.is_actor_bot = False
        self.is_bot_object = False
        self.msg_list_wcap = None
        self.msg_list = None
        self.cmd = None
        self.mentioned = False
        self.chat_room_id = None
        self.service_status = None
        self.actor_data = None
        if not body:
            return
        self.__rawbody = body.decode('utf-8', 'ignore')
        try:
            self.body = json.loads(self.__rawbody)
            logging.debug('Received Army Knife webhook: ' + self.__rawbody)
            self.data = self.body['data']
            self.person_id = self.body['actorId']
        except (TypeError, KeyError, ValueError):
            return
        if not self.data:
            return
        if 'personEmail' in self.data:
            self.person_object = self.data['personEmail'].lower()
            if self.person_object == self.config.bot['email'].lower():
                self.is_bot_object = True
                if self.person_id == self.data['personId']:
                    self.is_actor_bot = True
        if 'roomId' in self.data:
            self.room_id = self.data['roomId']  # id of existing room
            if 'roomType' in self.data:
                self.room_type = self.data['roomType']  # direct or group
        if 'id' in self.data:
            if self.body['resource'] == 'rooms':
                self.room_id = self.data['id']  # id of new room
            else:
                self.object_id = self.data['id']  # Could be message, membership or other object
            if 'type' in self.data:
                self.room_type = self.data['type']  # direct or group

    def re_init(self, actor_id=None, new_actor=None):
        self.bot_request = False
        if new_actor:
            self.me = new_actor
            self.actor_id = new_actor.id
        elif not actor_id and not self.person_id:
            return False
        elif not actor_id:
            self.me = actor.Actor(config=self.config)
            self.bot_request = True
            self.me.get_from_property(name='oauthId', value=self.person_id)
            if self.me.id:
                logging.debug('Found Actor(' + self.me.id + ')')
            else:
                self.me = None
                return False
            self.actor_id = self.me.id
        elif actor_id:
            self.actor_id = actor_id
        self.is_actor_user = True
        self.link = ciscowebexteams.CiscoWebexTeams(auth=self.auth, actor_id=self.actor_id, config=self.config)
        self.store = armyknife.ArmyKnife(actor_id=self.actor_id, config=self.config)
        return True

    def check_bot_signature(self, headers=None, raw_body=''):
        if headers and self.__signature_header in headers:
            sign = headers[self.__signature_header]
        else:
            logging.warning('Got an unsigned bot message! (' + str(headers) + ')')
            return False
        key = self.config.bot['secret'].encode('utf-8')
        msghash = hmac.new(key=key, msg=raw_body, digestmod=hashlib.sha1)
        if msghash.hexdigest() != sign:
            logging.warning('Signature does not match on bot message!')
            # self.link.post_admin_message(text='SECURITY ALERT: Got bot message with non-matching signature')
            return False
        logging.debug('Got signed and verified bot message')
        return True

    def check_firehose_signature(self, headers=None, raw_body=''):
        if self.__signature_header in headers:
            sign = headers[self.__signature_header]
        else:
            sign = None
        if sign and len(sign) > 0:
            myhash = hashlib.sha256()
            myhash.update(self.me.passphrase.encode('utf-8'))
            msghash = hmac.new(key=myhash.hexdigest().encode('utf-8'), msg=raw_body, digestmod=hashlib.sha1)
            if msghash.hexdigest() == sign:
                logging.debug('Got signed and verified firehose message')
                return True
            else:
                logging.debug('Signature does not match on firehose message' + str(sign))
                # Do not accept this message as it may be an attacker
                return False
        else:
            logging.debug("Got firehose without signature...")

    def enrich_data(self, what=None):
        """ Retrieve data from Army Knife. This operation has a cost of
        roundtrip to Army Knife platform."""
        if what == 'me' and not self.actor_data:
            self.actor_data = self.link.get_me()
            if self.me and not self.actor_data or 'displayName' not in self.actor_data:
                self.me.property.service_status = 'invalid'
                last_err = self.link.last_response()
                logging.error("Was not able to retrieve personal (me) data to enrich "
                              "from Army Knife. Code(" + str(last_err['code']) +
                              ") - " + last_err['message'])
                return False
            if self.actor_data:
                logging.debug("Enriched with Army Knife me data: " + str(self.actor_data))
        if what == 'person' and not self.person_data and self.person_id:
            self.person_data = self.link.get_person(self.person_id)
            if self.me and not self.person_data:
                self.me.property.service_status = 'invalid'
                last_err = self.link.last_response()
                logging.error("Was not able to retrieve person data to enrich from Army Knife. Code(" + str(
                        last_err['code']) +
                    ") - " + last_err['message'])
                return False
            if self.person_data:
                logging.debug("Enriched with person data: " + str(self.person_data))
                if 'emails' in self.person_data:
                    if self.person_data['emails'][0].lower() == self.config.bot['email'].lower():
                        self.person_data = None
                        self.is_actor_bot = True
                        return False
        if what == 'room' and not self.room_data and self.room_id:
            self.room_data = self.link.get_room(self.room_id)
            if self.me and not self.room_data or 'title' not in self.room_data:
                self.me.property.service_status = 'invalid'
                self.room_type = ''
                last_err = self.link.last_response()
                logging.error("Was not able to retrieve room data to enrich from Army Knife. Code(" +
                              str(last_err['code']) + ") - " + str(last_err['message']))
                return False
            elif 'type' in self.room_data:
                self.room_type = self.room_data['type']
            if self.room_data and 'id' in self.room_data:
                logging.debug("Enriched with room data in room_id: " + str(self.room_data['id']))
        if what == 'msg' and not self.msg_data and self.object_id:
            self.msg_data = self.link.get_message(self.object_id)
            if self.me and (not self.msg_data or 'text' not in self.msg_data):
                last_err = self.link.last_response()
                logging.error("Was not able to retrieve message data to enrich from Army Knife. Code(" + str(
                        last_err['code']) +
                    ") - " + last_err['message'].decode('utf-8'))
                if last_err['code'] == 400:
                    self.me.property.service_status = 'invalid'
                    now = datetime.datetime.utcnow()
                    token_invalid = self.me.property.token_invalid
                    if not token_invalid or token_invalid != now.strftime("%Y%m%d"):
                        self.me.property.token_invalid = now.strftime("%Y%m%d")
                        self.link.post_bot_message(
                            email=self.me.creator,
                            text="Your Army Knife Army Knife account has no longer access. Please type "
                                 "/init in this room to re-authorize the account.")
                        self.link.post_bot_message(
                            email=self.me.creator,
                            text="If you repeatedly get this error message, do /delete DELETENOW "
                                 "before a new /init. This will reset your account (note: all settings as well).")
                        logging.info("User (" + self.me.creator + ") has invalid refresh token and got notified.")
                return False
            if self.msg_data and 'personEmail' in self.msg_data:
                logging.debug("Enriched with message data from: " + str(self.msg_data['personEmail'].lower()))
            if not self.msg_data or 'text' not in self.msg_data:
                logging.debug('Failed to retrieve message and self.me not set!')
                return False
            self.msg_list = self.msg_data['text'].lower().split(" ")
            self.msg_list_wcap = self.msg_data['text'].split(" ")
            if fargate.in_fargate() and self.msg_list[0] == '/fargate':
                del self.msg_list[0]
                del self.msg_list_wcap[0]
            if self.room_type == 'direct':
                self.cmd = self.msg_list[0]
            else:
                if len(self.msg_list) < 1:
                    # No command
                    return True
                # @mention /cmd
                if self.bot_request:
                    if len(self.msg_list) == 1:
                        return True
                    self.cmd = self.msg_list[1]
                else:
                    self.cmd = self.msg_list[0]
            if self.me and self.me.creator and '/' in self.cmd:
                logging.debug('Received command from ' + self.me.creator + ': ' + self.cmd)
            elif '/' in self.cmd:
                logging.debug('Received command from unknown user: ' + self.cmd)
        if what == 'account' and not self.chat_room_id and self.me:
            self.chat_room_id = self.me.property.chatRoomId
            self.actor_spark_id = self.me.property.oauthId
            self.service_status = self.me.property.service_status
            logging.debug("Enriched with ArmyKnife user data (chatroom_id:" + (self.chat_room_id or '-') +
                          ") (spark_id:" + (self.actor_spark_id or '') + ") (service_status:" +
                          (self.service_status or '') + ")")
        return True
