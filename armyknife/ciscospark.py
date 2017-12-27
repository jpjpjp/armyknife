from actingweb import auth as botauth


# This class relies on an actingweb oauth object to use for sending oauth data requests
class ciscospark():

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
        self.botAuth = botauth.Auth(id=None, config=self.config)
        self.botAuth.oauth.token = self.config.bot['token']

    def lastResponse(self):
        return {
            'code': self.auth.oauth.last_response_code,
            'message': self.auth.oauth.last_response_message,
        }

    def getMe(self):
        return self.auth.oauth_get(self.spark['me_uri'])

    def getPerson(self, id=None):
        if not id:
            return False
        return self.auth.oauth_get(self.spark['person_uri'] + '/' + id)

    def createRoom(self, room_title=None, teamId=None):
        if not room_title:
            return False
        params = {
            'title': room_title,
        }
        if teamId:
            params['teamId'] = teamId
        return self.auth.oauth_post(self.spark['room_uri'], params=params)

    def deleteRoom(self, id=None):
        if not id:
            return False
        return self.auth.oauth_delete(self.spark['room_uri'] + '/' + id)

    def getRoom(self, id=None):
        if not id:
            return False
        return self.auth.oauth_get(self.spark['room_uri'] + '/' + id)

    def getRooms(self, get_next=False):
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

    def getMemberships(self, id=None, email=None, get_next=False):
        if not id and not email and not get_next:
            return False
        params = None
        if get_next:
            url = self.auth.oauth.next
        else:
            url = self.spark['membership_uri']
            params = {
                'max': 2,
            }
        if id:  
            params = {
                'roomId': id,
            }
        elif email:
            params = {
                'personEmail': email,
            }
        return self.auth.oauth_get(url=url, params=params)

    def addMember(self, id=None, email=None, personId=None):
        if not id or (not email and not personId):
            return False
        if email:
            params = {
                'roomId': id,
                'personEmail': email,
            }
        elif personId:
            params = {
                'roomId': id,
                'personId': personId,
            }
        return self.auth.oauth_post(self.spark['membership_uri'], params=params)

    def deleteMember(self, id=None):
        if not id:
            return False
        return self.auth.oauth_delete(self.spark['membership_uri'] + '/' + id)

    def messageUser(self, email=None, text='', markdown=False):
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

    def postMessage(self, id=None, text='', markdown=False, files=None):
        if not id:
            return False
        if markdown:
            params = {
                'roomId': id,
                'markdown': text,
            }
        else:
            params = {
                'roomId': id,
                'text': text,
            }
        if files:
            params = {
                'files': files,
            }
        return self.auth.oauth_post(self.spark['message_uri'], params=params)

    def postAdminMessage(self, text='', markdown=False, files=None):
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

    def postBotMessage(self, email=None, roomId=None, text='', markdown=False, files=None):
        if not email and not roomId:
            return False
        if email:
            params = {
                'toPersonEmail': email,
            }
        else:
            params = {
                'roomId': roomId,
            }
        if markdown:
            params['markdown'] = text
        else:
            params['text'] = text
        if files:
            params = {
                'files': files,
            }
        return self.botAuth.oauth_post(self.spark['message_uri'], params=params)

    def getMessage(self, id=None):
        if not id:
            return False
        return self.auth.oauth_get(self.spark['message_uri'] + '/' + id)

    def deleteMessage(self, id=None):
        if not id:
            return False
        return self.auth.oauth_delete(self.spark['message_uri'] + '/' + id)

    def getMessages(self, roomId=None, beforeId=None, beforeDate=None, max=10):
        if not roomId:
            return False
        params = {
            'roomId': roomId,
            'max': max,
        }
        if max == 0:
            del params['max']
            params = {}
            url = self.auth.oauth.next
        else:
            url = self.spark['message_uri']
        if beforeId:
            params.update({'beforeMessage': beforeId})
        elif beforeDate:
            params.update({'before': beforeDate})
        results = self.auth.oauth_get(url, params=params)
        if results and 'items' in results:
            return results['items']
        else:
            return None

    def getAttachmentDetails(self, url=None):
        if not url or len(url) == 0:
            return None
        return self.auth.oauth_head(url)

    def registerWebHook(self, name=None, target=None, resource='messages', event='created', filter='', secret=None):
        if not target or not name:
            return None
        params = {
            'name': name,
            'targetUrl': target,
            'resource': resource,
            'event': event,
            'filter': filter,
        }
        if secret and len(secret) > 0:
            params['secret'] = secret
        if len(filter) == 0:
            del params['filter']
        return self.auth.oauth_post(self.spark['webhook_uri'], params=params)

    def unregisterWebHook(self, id=None):
        if not id:
            return None
        return self.auth.oauth_delete(self.spark['webhook_uri'] + '/' + id)

    def getWebHook(self, id):
        return self.auth.oauth_get(self.spark['webhook_uri'] + "/" + id)

    def getAllWebHooks(self, max=100, uri=None):
        if uri:
            params = None
        else:
            uri = self.spark['webhook_uri']
            params = {
                'max': max,
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

    def cleanAllWebhooks(self, id=False):
        ret = self.getAllWebHooks()
        while 1:
            if not ret:
                break
            for webhook in ret['webhooks']:
                self.unregisterWebHook(id=webhook['id'])
            if not ret['next']:
                break
            ret = self.getAllWebHooks(uri=ret['next'])
        if id:
            self.postBotMessage(roomId=id, text='Completed clean up of webhooks.')
