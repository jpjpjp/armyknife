import webapp2
from actingweb import aw_web_request
from actingweb.handlers import callbacks
from armyknife import on_aw


# noinspection PyAttributeOutsideInit
class ActorCallbacks(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = callbacks.CallbacksHandler(self.obj, self.app.registry.get('config'),
                                                  on_aw=on_aw.OnAWWebexTeams())

    def get(self, actor_id, name):
        self.init()
        # Process the request
        self.handler.get(actor_id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        if self.obj.response.status_code == 404:
            return
        template = None
        if name == 'joinroom':
            template = self.app.registry.get('template').get_template('spark-joinroom.html')
        elif name == 'makefilepublic':
            template = self.app.registry.get('template').get_template('spark-getattachment.html')
        if template:
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.write(self.obj.response.body)

    def put(self, actor_id, name):
        self.init()
        # Process the request
        self.handler.put(actor_id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, actor_id, name):
        self.init()
        # Process the request
        self.handler.delete(actor_id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, actor_id, name):
        self.init()
        # Process the request
        self.handler.post(actor_id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        template = None
        if name == 'joinroom':
            template = self.app.registry.get('template').get_template(
                self.obj.response.template_values["template_path"])
            del self.obj.response.template_values["template_path"]
        if template:
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.write(self.obj.response.body)
