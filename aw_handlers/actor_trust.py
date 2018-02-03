import webapp2
from actingweb import aw_web_request
from actingweb.handlers import trust

# /trust aw_handlers
#
# GET /trust with query parameters (relationship, type, and peerid) to retrieve trust relationships (auth:
# only creator and admins allowed)
# POST /trust with json body to initiate a trust relationship between this
#   actor and another (reciprocal relationship) (auth: only creator and admins allowed)
# POST /trust/{relationship} with json body to create new trust
#   relationship (see config.py for default relationship and auto-accept, no
#   auth required)
# GET /trust/{relationship}}/{actorid} to get details on a specific relationship (auth: creator, admin, or peer secret)
# POST /trust/{relationship}}/{actorid} to send information to a peer about changes in the relationship
# PUT /trust/{relationship}}/{actorid} with a json body to change details on a relationship (baseuri, secret, desc)
# (auth: creator,
#   admin, or peer secret)
# DELETE /trust/{relationship}}/{actorid} to delete a relationship (with
#   ?peer=true if the delete is from the peer) (auth: creator, admin, or
#   peer secret)


# Handling requests to trust/
# noinspection PyAttributeOutsideInit
class ActorTrust(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.TrustHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id):
        self.init()
        # Process the request
        self.handler.get(actor_id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id):
        self.init()
        # Process the request
        self.handler.post(actor_id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# Handling requests to /trust/*, e.g. /trust/friend
# noinspection PyAttributeOutsideInit
class ActorTrustRelationships(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.TrustRelationshipHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, relationship):
        self.init()
        # Process the request
        self.handler.get(actor_id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, actor_id, relationship):
        self.init()
        # Process the request
        self.handler.put(actor_id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id, relationship):
        self.init()
        # Process the request
        self.handler.delete(actor_id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id, relationship):
        self.init()
        # Process the request
        self.handler.post(actor_id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# Handling requests to specific relationships, e.g. /trust/friend/12f2ae53bd
# noinspection PyAttributeOutsideInit
class ActorTrustPeer(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.TrustPeerHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.get(actor_id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.post(actor_id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, actor_id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.put(actor_id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.delete(actor_id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)
