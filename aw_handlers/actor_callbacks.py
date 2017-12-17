import webapp2
import json
from actingweb import aw_web_request
from actingweb import actor
from actingweb.handlers import callbacks
import on_aw

class actor_callbacks(webapp2.RequestHandler):

    def init(self):
        self.obj=aw_web_request.aw_webobj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)
        self.handler = callbacks.callbacks_handler(self.obj, self.app.registry.get('config'), on_aw=on_aw.spark_on_aw)

    def get(self, id, name):
        self.init()
        # Process the request
        self.handler.get(id, name)
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

    def put(self, id, name):
        self.init()
        # Process the request
        self.handler.put(id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def delete(self, id, name):
        self.init()
        # Process the request
        self.handler.delete(id, name)
        # Pass results back to webapp2
        self.response.set_status(self.obj.response.status_code, self.obj.response.status_message)
        self.response.headers = self.obj.response.headers
        self.response.write(self.obj.response.body)

    def post(self, id, name):
        self.init()
        myself = actor.actor(id=id, config=self.app.registry.get('config'))
        if not myself or not myself.id:
            email = json.loads(self.request.body.decode('utf-8', 'ignore'))['data']['personEmail']
            migrate = requests.get('https://spark-army-knife.appspot.com/migration/' + email,
                                   headers={
                                      'Authorization': 'Bearer 65kN%57ItPNSQVHS',
                                   })
            if migrate:
                properties = migrate.json()
                myself = actor.actor(config=self.app.registry.get('config').newToken())
                myself.create(url=self.request.url, passphrase=self.app.registry.get('config').newToken(), creator=email)
                for p, v in properties.iteritems():
                    if p == 'migrated':
                        continue
                    try:
                        v = json.dumps(v)
                    except:
                        pass
                    myself.setProperty(p, v)
                logging.debug("Successfully migrated " + email)
        # Process the request
        self.handler.post(id, name)
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