import webapp2
from actingweb import aw_web_request
from actingweb.handlers import devtest


# noinspection PyAttributeOutsideInit
class Devtests(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = devtest.DevtestHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, path):
        self.init()
        # Process the request
        self.handler.get(actor_id, path)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def put(self, actor_id, path):
        self.init()
        # Process the request
        self.handler.put(actor_id, path)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id, path):
        self.init()
        # Process the request
        self.handler.delete(actor_id, path)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id, path):
        self.init()
        # Process the request
        self.handler.post(actor_id, path)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)
