import logging
from actingweb import auth as botauth


# This class relies on an actingweb oauth object to use for sending oauth data requests
class CiscoWebexTeams:

    def __init__(self, auth, actor_id, config):
        self.actor_id = actor_id
        self.auth = auth
        self.spark = {
            'me_uri': "https://api.ciscospark.com/v1/people/me",
            'room_uri': "https://api.ciscospark.com/v1/rooms",
            'message_uri': "https://api.ciscospark.com/v1/messages",
            'webhook_uri': "https://api.ciscospark.com/v1/webhooks",
            'person_uri': "https://api.ciscospark.com/v1/people",
            'membership_uri': "https://api.ciscospark.com/v1/memberships",
        }
        self.config = config
        self.botAuth = botauth.Auth(actor_id=None, config=self.config)
        self.botAuth.oauth.token = self.config.bot['token']

    def last_response(self):
        return {
            'code': self.auth.oauth.last_response_code,
            'message': self.auth.oauth.last_response_message,
        }

    def get_me(self):
        return self.auth.oauth_get(self.spark['me_uri'])

    def get_person(self, spark_id=None):
        if not spark_id:
            return False
        return self.auth.oauth_get(self.spark['person_uri'] + '/' + spark_id)

    def create_room(self, room_title=None, team_id=None):
        if not room_title:
            return False
        params = {
            'title': room_title,
        }
        if team_id:
            params['teamId'] = team_id
        return self.auth.oauth_post(self.spark['room_uri'], params=params)

    def delete_room(self, spark_id=None):
        if not spark_id:
            return False
        return self.auth.oauth_delete(self.spark['room_uri'] + '/' + spark_id)

    def get_room(self, spark_id=None):
        if not spark_id:
            return False
        return self.auth.oauth_get(self.spark['room_uri'] + '/' + spark_id)

    def get_rooms(self, get_next=False):
        if get_next:
            url = self.auth.oauth.next
        else:
            url = self.spark['room_uri']
        if not get_next:
            params = {
                'type': 'group',
                'max': 400,
            }
        else:
            params = None
        return self.auth.oauth_get(url=url, params=params)

    def get_memberships(self, spark_id=None, email=None, get_next=False):
        if not spark_id and not email and not get_next:
            return False
        params = None
        if get_next:
            url = self.auth.oauth.next
        else:
            url = self.spark['membership_uri']
            params = {
                'max': 100,
            }
        if spark_id:
            params = {
                'roomId': spark_id,
            }
        elif email:
            params = {
                'personEmail': email,
            }
        return self.auth.oauth_get(url=url, params=params)

    def add_member(self, spark_id=None, email=None, person_id=None):
        if not spark_id or (not email and not person_id):
            return False
        params = None
        if email:
            params = {
                'roomId': spark_id,
                'personEmail': email,
            }
        elif person_id:
            params = {
                'roomId': spark_id,
                'personId': person_id,
            }
        return self.auth.oauth_post(self.spark['membership_uri'], params=params)

    def delete_member(self, spark_id=None):
        if not spark_id:
            return False
        return self.auth.oauth_delete(self.spark['membership_uri'] + '/' + spark_id)

    def message_user(self, email=None, text='', markdown=False):
        if not email:
            return False
        if markdown:
            params = {
                'toPersonEmail': email,
                'markdown': text,
            }
        else:
            params = {
                'toPersonEmail': email,
                'text': text,
            }
        return self.auth.oauth_post(self.spark['message_uri'], params=params)

    def post_message(self, spark_id=None, text='', markdown=False, files=None):
        if not spark_id:
            return False
        if markdown:
            params = {
                'roomId': spark_id,
                'markdown': text,
            }
        else:
            params = {
                'roomId': spark_id,
                'text': text,
            }
        if files:
            params = {
                'files': files,
            }
        return self.auth.oauth_post(self.spark['message_uri'], params=params)

    def post_admin_message(self, text='', markdown=False, files=None):
        if not self.config.bot["admin_room"] or len(self.config.bot["admin_room"]) == 0:
            return False
        if markdown:
            params = {
                'roomId': self.config.bot["admin_room"],
                'markdown': text,
            }
        else:
            params = {
                'roomId': self.config.bot["admin_room"],
                'text': text,
            }
        if files:
            params = {
                'files': files,
            }
        return self.botAuth.oauth_post(self.spark['message_uri'], params=params)

    def post_bot_message(self, email=None, spark_id=None, text='', markdown=False, files=None, card=None):
        if not email and not spark_id:
            return False
        if email:
            params = {
                'toPersonEmail': email,
            }
        else:
            params = {
                'roomId': spark_id,
            }
        if markdown:
            params['markdown'] = text
        else:
            params['text'] = text
        if files:
            params = {
                'files': files,
            }
        if card:
            params['attachments'] = [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card
                    }
                ]
        return self.botAuth.oauth_post(self.spark['message_uri'], params=params)

    def get_message(self, spark_id=None):
        if not spark_id:
            return False
        ret = self.auth.oauth_get(self.spark['message_uri'] + '/' + spark_id)
        if self.auth.oauth.last_response_code == 404:
            refresh = self.auth.oauth.oauth_refresh_token(refresh_token=self.auth.refresh_token)
            if not refresh:
                logging.warning('Tried token refresh based on 404 from Army Knife, but failed')
            else:
                ret = self.auth.oauth_get(self.spark['message_uri'] + '/' + spark_id)
        return ret

    def delete_message(self, spark_id=None):
        if not spark_id:
            return False
        return self.auth.oauth_delete(self.spark['message_uri'] + '/' + spark_id)

    def get_messages(self, spark_id=None, before_id=None, before_date=None, max_msgs=10):
        if not spark_id:
            return False
        params = {
            'roomId': spark_id,
            'max': max_msgs,
        }
        if max_msgs == 0:
            del params['max']
            params = {}
            url = self.auth.oauth.next
        else:
            url = self.spark['message_uri']
        if before_id:
            params.update({'beforeMessage': before_id})
        elif before_date:
            params.update({'before': before_date})
        results = self.auth.oauth_get(url, params=params)
        if results and 'items' in results:
            return results['items']
        else:
            return None

    def get_attachment_details(self, url=None):
        if not url or len(url) == 0:
            return None
        return self.auth.oauth_head(url)

    def register_webhook(self, name=None, target=None, resource='messages', event='created', webhook_filter='',
                         secret=None):
        if not target or not name:
            return None
        params = {
            'name': name,
            'targetUrl': target,
            'resource': resource,
            'event': event,
            'filter': webhook_filter,
        }
        if secret and len(secret) > 0:
            params['secret'] = secret
        if len(webhook_filter) == 0:
            del params['filter']
        return self.auth.oauth_post(self.spark['webhook_uri'], params=params)

    def unregister_webhook(self, spark_id=None):
        if not spark_id:
            return None
        return self.auth.oauth_delete(self.spark['webhook_uri'] + '/' + spark_id)

    def get_webhook(self, spark_id):
        return self.auth.oauth_get(self.spark['webhook_uri'] + "/" + spark_id)

    def get_all_webhooks(self, max_webhooks=100, uri=None):
        if uri:
            params = None
        else:
            uri = self.spark['webhook_uri']
            params = {
                'max': max_webhooks,
            }
        results = self.auth.oauth_get(uri, params)
        if results:
            ret = {
                'webhooks': results['items'],
                'next': self.auth.oauth.next,
                'prev': self.auth.oauth.prev,
                'first': self.auth.oauth.first,
            }
            return ret
        else:
            return None

    def clean_all_webhooks(self, spark_id=False):
        ret = self.get_all_webhooks()
        while 1:
            if not ret:
                break
            for webhook in ret['webhooks']:
                self.unregister_webhook(spark_id=webhook['id'])
            if not ret['next']:
                break
            ret = self.get_all_webhooks(uri=ret['next'])
        if spark_id:
            self.post_bot_message(spark_id=spark_id, text='Completed clean up of webhooks.')
