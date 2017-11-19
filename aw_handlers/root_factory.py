import webapp2
from actingweb import aw_web_request
from actingweb.handlers import factory


class root_factory(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = factory.root_factory_handler(self.obj, self.app.registry.get('config'))


    def get(self):
        self.init()
        # Process the request
        self.handler.get()
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        template = self.app.registry.get('template').get_template('aw-root-factory.html')
        self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))

    def post(self):
        self.init()
        # Process the request
        self.handler.post()
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        if len(self.obj.response.template_values) > 0:
            template = self.app.registry.get('template').get_template('aw-root-created.html')
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.write(self.obj.response.body)
        if self.obj.response.redirect:
            self.redirect(self.obj.response.redirect)

