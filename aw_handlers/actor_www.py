import webapp2
from actingweb import aw_web_request
from actingweb.handlers import www


# noinspection PyAttributeOutsideInit
class ActorWWW(webapp2.RequestHandler):

    def init(self):
        cookies = {}
        raw_cookies = self.request.headers.get("Cookie")
        if raw_cookies:
            for cookie in raw_cookies.split(";"):
                name, value = cookie.split("=")
                cookies[name] = value
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers,
            cookies=cookies)
        self.handler = www.WwwHandler(self.obj, self.app.registry.get('config'))

    def get(self, actor_id, path):
        self.init()
        # Process the request
        self.handler.get(actor_id, path)
        # Pass results back to webapp2
        if len(self.obj.response.cookies) > 0:
            for a in self.obj.response.cookies:
                self.request.set_cookie(a["name"], a["value"], max_age=a["max_age"], secure=a["secure"])
        if self.obj.response.redirect:
            self.redirect(self.obj.response.redirect)
            return
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        template = None
        if not path or path == '':
            template = self.app.registry.get('template').get_template('aw-actor-www-root.html')
        elif path == 'init':
            template = self.app.registry.get('template').get_template('aw-actor-www-init.html')
        elif path == 'properties':
            template = self.app.registry.get('template').get_template('aw-actor-www-properties.html')
        elif path == 'property':
            template = self.app.registry.get('template').get_template('aw-actor-www-property.html')
        elif path == 'trust':
            template = self.app.registry.get('template').get_template('aw-actor-www-trust.html')
        elif path == 'getattachment':
            template = self.app.registry.get('template').get_template('spark-getattachment.html')
        if template:
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.write(self.obj.response.body)
