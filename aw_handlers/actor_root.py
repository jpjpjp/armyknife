import webapp2
from actingweb import aw_web_request
from actingweb.handlers import root


# noinspection PyAttributeOutsideInit
class ActorRoot(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = root.RootHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id):
        self.init()
        # Process the request
        self.handler.get(actor_id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id):
        self.init()
        # Process the request
        self.handler.delete(actor_id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)
