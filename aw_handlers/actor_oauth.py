import webapp2
from actingweb import aw_web_request
from actingweb.handlers import oauth
import on_aw


class actor_oauth(webapp2.RequestHandler):

    def init(self):
        cookies = {}
        raw_cookies = self.request.headers.get("Cookie")
        if raw_cookies:
            for cookie in raw_cookies.split(";"):
                name, value = cookie.split("=")
                cookies[name] = value
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers,
            cookies=cookies)
        self.handler = oauth.oauth_handler(self.obj, self.app.registry.get('config'), on_aw=on_aw.spark_on_aw)


    def get(self, id, path):
        self.init()
        # Process the request
        self.handler.get(id, path)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        # Since cookies are put into the headers, the headers must be set BEFORE doing set_cookie to avoid
        # being overwritten
        self.response.headers = self.obj.response.headers
        if len(self.obj.response.cookies) > 0:
            for a in self.obj.response.cookies:
                self.response.set_cookie(a["name"], a["value"], max_age=a["max_age"], secure=a["secure"])
        self.response.write(self.obj.response.body)
        if self.obj.response.redirect:
            self.redirect(self.obj.response.redirect)