import webapp2
from actingweb import aw_web_request

# noinspection PyAttributeOutsideInit
class Static(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)

    def get(self, file):
        self.init()
        template = self.app.registry.get('template').get_template(file)
        if '.css' in file:
            self.response.content_type = 'text/css'
        elif '.js' in file:
            self.response.content_type = 'application/javascript'
        self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))

