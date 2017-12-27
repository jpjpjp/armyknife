import webapp2
from actingweb import aw_web_request
from actingweb.handlers import subscription


# noinspection PyAttributeOutsideInit
class RootHandler(webapp2.RequestHandler):
    """Handles requests to /subscription"""

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.SubscriptionRootHandler(self.obj, self.app.registry.get('config'))

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


# Handling requests to /subscription/*, e.g. /subscription/<peerid>
# noinspection PyAttributeOutsideInit
class RelationshipHandler(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.SubscriptionRelationshipHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, peerid):
        self.init()
        # Process the request
        self.handler.get(actor_id, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id, peerid):
        self.init()
        # Process the request
        self.handler.post(actor_id, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# noinspection PyAttributeOutsideInit
class SubscriptionHandler(webapp2.RequestHandler):
    """ Handling requests to specific subscriptions, e.g. /subscriptions/<peerid>/12f2ae53bd"""

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.SubscriptionHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, peerid, subid):
        self.init()
        # Process the request
        self.handler.get(actor_id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, actor_id, peerid, subid):
        self.init()
        # Process the request
        self.handler.put(actor_id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id, peerid, subid):
        self.init()
        # Process the request
        self.handler.delete(actor_id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


# noinspection PyAttributeOutsideInit
class DiffHandler(webapp2.RequestHandler):
    """ Handling requests to specific diffs for one subscription and clears it, e.g.
    /subscriptions/<peerid>/<subid>/112"""

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.SubscriptionDiffHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, peerid, subid, seqnr):
        self.init()
        # Process the request
        self.handler.get(actor_id, peerid, subid, seqnr)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)
