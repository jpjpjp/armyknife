import json
import logging
import hashlib
from actingweb import on_aw
from . import webexrequest
from . import webexbothandler
from . import webexmessagehandler


class OnAWWebexTeams(object, on_aw.OnAWBase):

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
        firehose_id = spark.me.get_property('firehoseId').value
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
        current_id = spark.me.get_property('oauthId').value
        if not current_id:
            if 'emails' not in me:
                spark.me.delete_property('cookie_redirect')
                return False
            if spark.me.creator != me['emails'][0]:
                spark.me.delete_property('cookie_redirect')
                spark.me.delete_property('oauth_token')
                spark.me.delete_property('oauth_refresh_token')
                spark.me.delete_property('oauth_token_expiry')
                spark.me.delete_property('oauth_refresh_token_expiry')
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
                if not spark.me.get_property('oauthId').value:
                    spark.me.delete()
                return False
            spark.me.set_property('email', me['emails'][0])
            spark.me.set_property('oauthId', me['id'])
            if 'displayName' in me:
                spark.me.set_property('displayName', me['displayName'])
            if 'avatar' in me:
                spark.me.set_property('avatarURI', me['avatar'])
            if '@actingweb.net' not in me['emails'][0]:
                spark.link.post_admin_message(
                    text='New user just signed up: ' + me['displayName'] + ' (' + me['emails'][0] + ')')
        else:
            logging.debug("Actor's identity:" + current_id)
            if me['id'] != current_id:
                spark.me.delete_property('cookie_redirect')
                spark.me.delete_property('oauth_token')
                spark.me.delete_property('oauth_refresh_token')
                spark.me.delete_property('oauth_token_expiry')
                spark.me.delete_property('oauth_refresh_token_expiry')
                spark.link.post_bot_message(
                    email=spark.me.get_property('email').value,
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
        email = spark.me.get_property('email').value
        hook_id = spark.me.get_property('firehoseId').value
        spark.me.delete_property('token_invalid')
        spark.me.delete_property('service_status')
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
        msghash.update(spark.me.passphrase)
        hook = spark.link.register_webhook(
            name='Firehose',
            target=self.config.root + spark.me.id + '/callbacks/firehose',
            resource='all',
            event='all',
            secret=msghash.hexdigest()
            )
        if hook and hook['id']:
            logging.debug('Successfully registered messages firehose webhook')
            spark.me.set_property('firehoseId', hook['id'])
        else:
            logging.debug('Failed to register messages firehose webhook')
            spark.link.post_admin_message(text='Failed to register firehose for new user: ' + email)
            spark.link.post_bot_message(
                email=email,
                text="Hi there! Welcome to the **Army Knife**! \n\n"
                     "You have successfully authorized access.\n\nSend me commands starting with /. Like /help",
                markdown=True)
            return True
        spark.link.post_bot_message(
            email=email,
            text="Hi there! Welcome to the **Army Knife**! \n\n"
                 "You have successfully authorized access.\n\nSend me commands starting with /. Like /help",
            markdown=True)
        return True

    def bot_post(self, path):
        """Called on POSTs to /bot."""
        # Get a spark request object to do signature check
        spark = webexrequest.WebexTeamsRequest(body=self.webobj.request.body,
                                               auth=self.auth,
                                               myself=None,
                                               config=self.config)
        if not spark.check_bot_signature(self.webobj.request.headers, self.webobj.request.body):
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
        handler = webexbothandler.WebexTeamsBotHandler(spark)
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
        if spark.me.creator == self.config.bot['email'] or spark.me.creator == "creator":
            my_email = spark.me.get_property('email').value
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
            handler.message_actions()
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
                         " leaving!\n\nThis 1:1 cannot be deleted (Cisco Webex Teams feature), and you can any time type /init"
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
        if 'target' in data and data['target'] == 'properties':
            if 'subtarget' in data and data['subtarget'] == 'topofmind' and 'data' in data:
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
            return True
        if 'resource' in data:
            folder_id = data['resource']
            room = spark.store.load_room_by_boxfolder_id(folder_id=folder_id)
            if room and 'data' in data and 'suggested_txt' in data['data']:
                spark.link.post_message(room.id, '**From Box:** ' + data['data']['suggested_txt'], markdown=True)
            else:
                logging.warn('Was not able to post callback message to Cisco Webex Teams room.')
        else:
            logging.debug('No resource in received subscription data.')
        return True
