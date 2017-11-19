import webapp2
from actingweb import aw_web_request
from actingweb.handlers import www


class actor_www(webapp2.RequestHandler):

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
        self.handler = www.www_handler(self.obj, self.app.registry.get('config'))

    def get(self, id, path):
        self.init()
        # Process the request
        self.handler.get(id, path)
        # Pass results back to webapp2
        if len(self.obj.response.cookies) > 0:
            for a in self.obj.response.cookies:
                self.request.set_cookie(a["name"], a["value"], max_age=a["max_age"], secure=a["secure"])
        if self.obj.response.redirect:
            self.redirect(self.obj.response.redirect)
            return
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        if not path or path == '':
            template = self.app.registry.get('template').get_template('aw-actor-www-root.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        elif path == 'init':
            template = self.app.registry.get('template').get_template('aw-actor-www-init.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        elif path == 'properties':
            template = self.app.registry.get('template').get_template('aw-actor-www-properties.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        elif path == 'property':
            template = self.app.registry.get('template').get_template('aw-actor-www-property.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        elif path == 'trust':
            template = self.app.registry.get('template').get_template('aw-actor-www-trust.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.write(self.obj.response.body)