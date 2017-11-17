import webapp2
from actingweb import aw_web_request
from actingweb.handlers import subscription


class rootHandler(webapp2.RequestHandler):
    """Handles requests to /subscription"""

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.subscription_root_handler(self.obj, self.app.registry.get('config'))

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


# Handling requests to /subscription/*, e.g. /subscription/<peerid>
class relationshipHandler(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.subscription_relationship_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, peerid):
        self.init()
        # Process the request
        self.handler.get(id, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, id, peerid):
        self.init()
        # Process the request
        self.handler.post(id, peerid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


class subscriptionHandler(webapp2.RequestHandler):
    """ Handling requests to specific subscriptions, e.g. /subscriptions/<peerid>/12f2ae53bd"""

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.subscription_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, peerid, subid):
        self.init()
        # Process the request
        self.handler.get(id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, id, peerid, subid):
        self.init()
        # Process the request
        self.handler.put(id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, id, peerid, subid):
        self.init()
        # Process the request
        self.handler.delete(id, peerid, subid)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


class diffHandler(webapp2.RequestHandler):
    """ Handling requests to specific diffs for one subscription and clears it, e.g. /subscriptions/<peerid>/<subid>/112"""

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = subscription.subscription_diff_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, peerid, subid, seqnr):
        self.init()
        # Process the request
        self.handler.get(id, peerid, subid, seqnr)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


