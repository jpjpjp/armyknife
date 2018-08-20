import webapp2
from actingweb import aw_web_request
from armyknife import payments


# noinspection PyAttributeOutsideInit
class StripeHandler(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)

    def get(self):
        self.init()
        template = self.app.registry.get('template').get_template('stripe-form.html')
        template.globals['STATIC_PREFIX'] = '/static'
        template.globals['ACTOR_ID'] = self.request.GET.get('id')
        template.globals['AMOUNT'] = self.request.GET.get('amount')
        self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))

    def post(self):
        self.init()
        result = payments.process_card(
            actor_id=self.request.params['actor_id'],
            amount=self.request.params['amount'],
            token=self.request.params['stripeToken']
        )
        if result:
            template = self.app.registry.get('template').get_template('stripe-form-result.html')
            template.globals['STATIC_PREFIX'] = '/static'
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            self.response.set_status(400, 'Failed card processing')
