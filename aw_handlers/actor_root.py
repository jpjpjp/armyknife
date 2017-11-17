import webapp2
from actingweb import aw_web_request
from actingweb.handlers import root


class actor_root(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = root.root_handler(self.obj, self.app.registry.get('config'))

    def get(self, id):
        self.init()
        # Process the request
        self.handler.get(id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, id):
        self.init()
        # Process the request
        self.handler.delete(id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)


