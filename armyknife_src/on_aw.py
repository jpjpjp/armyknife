import json
import logging
import hashlib
from actingweb import on_aw
from armyknife_src import webexrequest
from armyknife_src import webexbothandler
from armyknife_src import webexmessagehandler
from armyknife_src import fargate

PROP_HIDE = [
    "email",
    "oauthId"
]

PROP_PROTECT = PROP_HIDE + [
    "service_status"
]


class OnAWWebexTeams(on_aw.OnAWBase):

    def get_properties(self, path: list, data: dict) -> dict or None:
        """ Called on GET to properties for transformations to be done
        :param path: Target path requested
        :type path: list[str]
        :param data: Data retrieved from data store to be returned
        :type data: dict
        :return: The transformed data to return to requestor or None if 404 should be returned
        :rtype: dict or None
        """
        if not path:
            for k, v in data.copy().items():
                if k in PROP_HIDE:
                    del data[k]
        elif len(path) > 0 and path[0] in PROP_HIDE:
            return None
        return data

    def delete_properties(self, path: list, old: dict, new: dict) -> bool:
        """ Called on DELETE to properties
        :param path: Target path to be deleted
        :type path: list[str]
        :param old: Property value that will be deleted (or changed)
        :type old: dict
        :param new: Property value after path has been deleted
        :type new: dict
        :return: True if DELETE is allowed, False if 403 should be returned
        :rtype: bool
        """
        if len(path) > 0 and path[0] in PROP_PROTECT:
            return False
        return True

    def put_properties(self, path: list, old: dict, new: dict) -> dict or None:
        """ Called on PUT to properties for transformations to be done before save
        :param path: Target path requested to be updated
        :type path: list[str]
        :param old: Old data from database
        :type old: dict
        :param new:
        :type new: New data from PUT request (after merge)
        :return: The dict that should be stored or None if 400 should be returned and nothing stored
        :rtype: dict or None
        """
        if not path:
            return None
        elif len(path) > 0 and path[0] in PROP_PROTECT:
            return None
        if path and len(path) >= 1 and path[0] == 'config':
            if 'watchLabels' in new:
                new_labels = new['watchLabels']
                gm = gmail.GMail(self.myself, self.config, self.auth)
                gm.create_watch(labels=new_labels, refresh=True)
        return new

    def post_properties(self, prop: str, data: dict) -> dict or None:
        """ Called on POST to properties, once for each property
        :param prop: Property to be created
        :type prop: str
        :param data: The data to be stored in prop
        :type data: dict
        :return: The transformed data to store in prop or None if that property should be skipped and not stored
        :rtype: dict or None
        """
        if not prop:
            return None
        elif prop in PROP_PROTECT:
            return None
        return data

    def delete_actor(self):
        """ Here we need to do additional cleanup when a user is deleted """
        spark = webexrequest.WebexTeamsRequest(
            body=self.webobj.request.body,
            auth=self.auth,
            myself=self.myself,
            config=self.config)
        spark.store.clear_messages(email=spark.me.creator)
        trackers = spark.store.load_trackers()
        for tracker in trackers:
            spark.store.delete_tracker(tracker["email"])
        firehose_id = spark.me.property.firehoseId
        if firehose_id:
            spark.link.unregister_webhook(firehose_id)
        spark.store.delete_rooms()
        spark.store.delete_pinned_messages()
        spark.store.delete_pinned_messages(comment="#/TOPOFMIND")
        if '@actingweb.net' not in spark.me.creator and spark.me.creator != "creator" and \
                spark.me.creator != "trustee":
            spark.link.post_admin_message(text='User just left: ' + spark.me.creator)
        return

    def www_paths(self, path=''):
        """ This method is called on the user's URL/www requests """
        # spark = sparkrequest.WebexTeamsRequest(body=self.webobj.request.body,
        #                     auth=self.auth,
        #                     myself=self.myself,
        #                     config=self.config)
        if path == '' or not self.myself:
            logging.info('Got an on_www_paths without proper parameters.')
            return False
        if path == 'getattachment':
            self.webobj.response.template_values = {
                'url': str(self.webobj.request.get('url')),
                'filename': str(self.webobj.request.get('filename')),
            }
            return True
        return False
    
    def check_on_oauth_success(self, token=None):
        """ Before approving an OAuth request, we need to validate the identity """

        spark = webexrequest.WebexTeamsRequest(
            body=self.webobj.request.body,
            auth=self.auth,
            myself=self.myself,
            config=self.config)
        me = spark.link.get_me()
        if not me:
            logging.debug("Not able to retrieve myself from Cisco Webex Teams!")
            return False
        logging.debug("My identity:" + me['id'])
        current_id = spark.me.property.oauthId
        if not current_id:
            if 'emails' not in me:
                spark.me.store.cookie_redirect = None
                return False
            if spark.me.creator.lower() != me['emails'][0].lower():
                spark.me.store.cookie_redirect = None
                spark.me.store.oauth_token = None
                spark.me.store.oauth_refresh_token = None
                spark.me.store.oauth_token_expiry = None
                spark.me.store.oauth_refresh_token_expiry = None
                spark.link.post_bot_message(
                    email=me['emails'][0],
                    text="**WARNING!!**\n\nAn attempt to create a new Army Knife account for " +
                         spark.me.creator +
                         " was done while you were logged into Cisco Webex Teams in your browser. Did you try with"
                         " the wrong email address?\n\n"
                         "You can instead do /init here to (re)authorize your account"
                         " (click the link to grant new access).",
                    markdown=True)
                spark.link.post_bot_message(
                    email=spark.me.creator,
                    text="**SECURITY WARNING**\n\n" + me['emails'][0] +
                         "'s Cisco Webex Teams credentials were attempted used to create a new Army Knife"
                         " account for you.\n\n"
                         "No action required, but somebody may have attempted to hijack your"
                         " Army Knife account.",
                    markdown=True)
                if not spark.me.property.oauthId:
                    spark.me.delete()
                return False
            spark.me.store.email = me['emails'][0].lower()
            spark.me.property.oauthId = me['id']
            if 'displayName' in me:
                spark.me.property.displayName = me['displayName']
            if 'avatar' in me:
                spark.me.property.avatarURI = me['avatar']
            if '@actingweb.net' not in me['emails'][0]:
                spark.link.post_admin_message(
                    text='New user just signed up: ' + me['displayName'] + ' (' + me['emails'][0] + ')')
        else:
            logging.debug("Actor's identity:" + current_id)
            if me['id'] != current_id:
                spark.me.store.cookie_redirect = None
                spark.me.store.oauth_token = None
                spark.me.store.oauth_refresh_token = None
                spark.me.store.oauth_token_expiry = None
                spark.me.store.oauth_refresh_token_expiry = None
                spark.link.post_bot_message(
                    email=spark.me.property.email,
                    text="**SECURITY WARNING**\n\n" + (me['emails'][0] or "Unknown") +
                         " tried to log into your Army Knife account.\n\n"
                         "For security reasons, your Army Knife account has been suspended.\n\n"
                         "If this happens repeatedly, please contact support@greger.io",
                    markdown=True)
                return False
        return True
    
    def actions_on_oauth_success(self):
        """ When OAuth is successfully done, we need to do several actions """

        if not self.myself:
            return True
        spark = webexrequest.WebexTeamsRequest(body=self.webobj.request.body,
                                               auth=self.auth,
                                               myself=self.myself,
                                               config=self.config)
        email = spark.me.creator
        hook_id = spark.me.property.firehoseId
        spark.me.property.token_invalid = None
        spark.me.property.service_status = None
        if hook_id:
            if spark.link.unregister_webhook(hook_id) is None and self.auth.oauth.last_response_code != 404 and \
                    self.auth.oauth.last_response_code != 0:
                spark.link.post_bot_message(
                    email=email,
                    text="Not able to delete old Cisco Webex Teams webhook link, do /init and authorize again "
                         "or do `/support your_msg` to get help",
                    markdown=True)
                spark.link.post_admin_message(
                    text="Successfully authorized account, but could not delete old firehose: " + email)
                spark.link.post_admin_message(
                    text=str(self.auth.oauth.last_response_code) + ':' + self.auth.oauth.last_response_message)
                return True
        msghash = hashlib.sha256()
        msghash.update(spark.me.passphrase.encode('utf-8'))
        hook = spark.link.register_webhook(
            name='Firehose',
            target=self.config.root + spark.me.id + '/callbacks/firehose',
            resource='all',
            event='all',
            secret=msghash.hexdigest()
            )
        if hook and hook['id']:
            logging.debug('Successfully registered messages firehose webhook')
            spark.me.property.firehoseId = hook['id']
        else:
            logging.debug('Failed to register messages firehose webhook')
            spark.link.post_admin_message(text='Failed to register firehose for new user: ' + email)
            spark.link.post_bot_message(
                email=email,
                text="Not able to create Cisco Webex Teams webhook link, do /init and authorize again "
                     "or do `/support your_msg` to get help",
                markdown=True)
            return True
        spark.me.property.app_disabled = None
        spark.link.post_bot_message(
            email=email,
            text="Hi there! Welcome to the **Army Knife**! \n\n"
                 "You have successfully authorized access.\n\nSend me commands starting with /. Like /help or /me",
            markdown=True)
        return True

    def bot_post(self, path):
        """Called on POSTs to /bot."""
        # Get a spark request object to do signature check
        spark = webexrequest.WebexTeamsRequest(body=self.webobj.request.body,
                                               auth=self.auth,
                                               myself=None,
                                               config=self.config)
        if not fargate.in_fargate() and not fargate.fargate_disabled() and \
                not spark.check_bot_signature(self.webobj.request.headers, self.webobj.request.body):
            return 404
        # Try to re-init from person_id in the message
        spark.re_init()
        # Ignore messages from the bot itself
        if spark.is_actor_bot:
            logging.debug("Dropping message from ArmyKnife bot...")
            return 204
        # If not successful, we don't have this user
        if not spark.is_actor_user:
            spark.enrich_data('person')
        #
        # The first time a user is in touch with the bot, it can either be the user or the bot that has initiated
        # the contact, i.e. the actor_id can either be somebody unknown or the bot
        # The message flow is the following:
        #   1. rooms, created -> type direct or group
        #   2. memberships, created -> two messages, one for the bot and one for the user
        #   3. messages, created -> either from the bot or from the user depending on who initiated the request
        #
        handler = webexbothandler.WebexTeamsBotHandler(spark, self.webobj)
        if spark.body['resource'] == 'rooms':
            if spark.body['event'] == 'created':
                handler.rooms_created()
        elif spark.body['resource'] == 'memberships':
            if spark.body['event'] == 'created':
                handler.memberships_created()
        elif spark.body['resource'] == 'messages':
            if spark.body['event'] == 'created':
                handler.messages_created()
        # No more event types we want to handle, just return
        return 204

    def get_callbacks(self, name):
        """ This method is called for regular web browser requests to the user's URL/something

        """
        spark = webexrequest.WebexTeamsRequest(body=self.webobj.request.body,
                                               auth=self.auth,
                                               myself=self.myself,
                                               config=self.config)
        if name == 'joinroom':
            uuid = self.webobj.request.get('id')
            room = spark.store.load_room_by_uuid(uuid)
            if not room:
                self.webobj.response.set_status(404)
                return True
            roominfo = spark.link.get_room(room['id'])
            self.webobj.response.template_values = {
                'id': uuid,
                'title': roominfo['title'],
            }
        if name == 'makefilepublic':
            pass
            # This is not secure!!! So do not execute
            # token is exposed directly in javascript in the users browser

            # self.webobj.response.template_values = {
            #    'url': str(self.webobj.request.get('url')),
            #    'token': str(auth.token),
            #    'filename': str(self.webobj.request.get('filename')),
            # }
        return True
    
    def post_callbacks(self, name):
        if not self.myself or not self.myself.id:
            logging.debug("Got a firehose callback for an unknown user.")
            self.webobj.response.set_status(410, 'Gone')
            return True
        spark = webexrequest.WebexTeamsRequest(
            body=self.webobj.request.body,
            auth=self.auth,
            myself=self.myself,
            config=self.config)
        # Ignore messages from the bot itself
        if spark.is_actor_bot:
            logging.debug("Dropping message from ArmyKnife bot...")
            return True
        # Clean up any actor creations from earlier where we got wrong creator email
        # Likely not needed anymore, but just in case
        if spark.me.creator.lower() == self.config.bot['email'].lower() or spark.me.creator == "creator":
            my_email = spark.me.property.email.lower()
            if my_email and len(my_email) > 0:
                spark.me.modify(creator=my_email)
        # Deprecated support for /callbacks/room
        if name == 'room':
            self.webobj.response.set_status(404, 'Not found')
            return True
        handler = webexmessagehandler.WebexTeamsMessageHandler(spark, self.webobj)
        # non-json POSTs to be handled first
        if name == 'joinroom':
            return handler.joinroom()
        if not spark.check_firehose_signature(self.webobj.request.headers, self.webobj.request.body):
            logging.debug('Returning 403 forbidden...')
            return False
        if spark.body['resource'] == 'memberships':
            if spark.body['event'] == 'created':
                handler.memberships_created()
            else:
                # memberships:deleted
                return True
        elif spark.body['resource'] == 'messages':
            # If message_actions() returns False, the account was disabled or invalid
            if not handler.message_actions():
                return True
        # Only handle messages:created events below
        if spark.body['resource'] != 'messages' or spark.body['event'] != 'created':
            return True
        # Special case for /delete as we need to call self.delete_actor()
        # Make sure we have pulled down the message and spark.cmd is thus set
        if not spark.enrich_data('msg'):
            return True
        if not spark.enrich_data('account'):
            return True
        if spark.cmd == '/delete' and spark.room_id == spark.chat_room_id:
            if len(spark.msg_list) == 2 and spark.msg_list_wcap[1] == 'DELETENOW':
                self.delete_actor()
                spark.me.delete()
                spark.link.post_bot_message(
                    email=spark.me.creator,
                    text="All your account data and the Cisco Webex Teams webhook was deleted. Sorry to see you"
                         " leaving!\n\nThis 1:1 cannot be deleted (Cisco Webex Teams feature), "
                         "and you can any time type /init"
                         " here to register a new account.",
                    markdown=True)
            else:
                spark.link.post_bot_message(
                    email=spark.me.creator,
                    text="Usage: `/delete DELETENOW`", markdown=True)
        if spark.body['resource'] == 'messages' and spark.body['event'] == 'created':
            handler.messages_created()
        # Successfully processed, just not acted upon
        self.webobj.response.set_status(204, 'No content')
        return True
    
    def post_subscriptions(self, sub, peerid, data):
        """Customizible function to process incoming callbacks/subscriptions/ callback with json body,
            return True if processed, False if not."""
        spark = webexrequest.WebexTeamsRequest(
            body=self.webobj.request.body,
            auth=self.auth,
            myself=self.myself,
            config=self.config)
        logging.debug("Got callback and processed " + sub["subscriptionid"] +
                      " subscription from peer " + peerid + " with json blob: " + json.dumps(data))
        app_disabled = spark.me.property.app_disabled
        if app_disabled and app_disabled.lower() == 'true':
            logging.debug("Account is disabled: " + spark.me.creator)
            return True
        if 'target' in data and data['target'] == 'properties':
            if 'subtarget' in data:
                if data['subtarget'] == 'topofmind' and 'data' in data:
                    topofmind = data['data']
                    toplist = topofmind['list']
                    if len(toplist) == 0:
                        spark.link.post_bot_message(
                            email=spark.me.creator,
                            text=topofmind['displayName'] + " (" + topofmind['email'] + ") just cleared " +
                            topofmind['title'], markdown=True)
                        return True
                    out = topofmind['displayName'] + " (" + topofmind['email'] + ") just updated " + topofmind[
                        'title'] + "\n\n----\n\n"
                    for i, el in sorted(toplist.items()):
                        out = out + "**" + i + "**: " + el + "\n\n"
                    spark.link.post_bot_message(email=spark.me.creator, text=out, markdown=True)
                elif data['subtarget'] == 'new' and 'data' in data:
                    out = '#Incoming email(s):  \n'
                    for k, v in data['data'].items():
                        h = v['headers']
                        out += '**From: ' + h['From'][0] + '**  \n'
                        out += 'Subject: ' + h['Subject'][0] + '  \n'
                        out += v['snippet'] + '\n\n---\n\n'
                        if len(out) > 4000:
                            spark.link.post_bot_message(email=spark.me.creator, text=out, markdown=True)
                            out = ''
                    if out:
                        spark.link.post_bot_message(email=spark.me.creator, text=out, markdown=True)
                return True
        if 'resource' in data:
            folder_id = data['resource']
            room = spark.store.load_room_by_boxfolder_id(folder_id=folder_id)
            if room and 'data' in data and 'suggested_txt' in data['data']:
                spark.link.post_message(room.id, '**From Box:** ' + data['data']['suggested_txt'], markdown=True)
            else:
                logging.warning('Was not able to post callback message to Cisco Webex Teams room.')
        else:
            logging.debug('No resource in received subscription data.')
        return True
