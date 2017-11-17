import webapp2
from actingweb import aw_web_request
from actingweb.handlers import callback_oauth


class callback_oauth(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = callback_oauth.callback_oauth_handler(self.obj, self.app.registry.get('config'))

    def get(self):
        self.init()
        # Process the request
        self.handler.get(id)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)
        if self.obj.redirect:
            self.redirect(self.obj.redirect)
