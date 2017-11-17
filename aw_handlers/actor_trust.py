import webapp2
from actingweb import aw_web_request
from actingweb.handlers import trust



# /trust aw_handlers
#
# GET /trust with query parameters (relationship, type, and peerid) to retrieve trust relationships (auth: only creator and admins allowed)
# POST /trust with json body to initiate a trust relationship between this
#   actor and another (reciprocal relationship) (auth: only creator and admins allowed)
# POST /trust/{relationship} with json body to create new trust
#   relationship (see config.py for default relationship and auto-accept, no
#   auth required)
# GET /trust/{relationship}}/{actorid} to get details on a specific relationship (auth: creator, admin, or peer secret)
# POST /trust/{relationship}}/{actorid} to send information to a peer about changes in the relationship
# PUT /trust/{relationship}}/{actorid} with a json body to change details on a relationship (baseuri, secret, desc) (auth: creator,
#   admin, or peer secret)
# DELETE /trust/{relationship}}/{actorid} to delete a relationship (with
#   ?peer=true if the delete is from the peer) (auth: creator, admin, or
#   peer secret)

# Handling requests to trust/
class actor_trust(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.trust_handler(self.obj, self.app.registry.get('config'))

    def get(self, id):
        self.init()
        # Process the request
        self.handler.get(id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, id):
        self.init()
        # Process the request
        self.handler.post(id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# Handling requests to /trust/*, e.g. /trust/friend
class actor_trust_relationships(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.trust_relationships_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, relationship):
        self.init()
        # Process the request
        self.handler.get(id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, id, relationship):
        self.init()
        # Process the request
        self.handler.put(id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, id, relationship):
        self.init()
        # Process the request
        self.handler.delete(id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, id, relationship):
        self.init()
        # Process the request
        self.handler.post(id, relationship)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# Handling requests to specific relationships, e.g. /trust/friend/12f2ae53bd
class actor_trust_peer(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = trust.trust_peer_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.get(id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.post(id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.put(id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, id, relationship, peerid):
        self.init()
        # Process the request
        self.handler.delete(id, relationship, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


