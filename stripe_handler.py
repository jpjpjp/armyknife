import webapp2
from actingweb import aw_web_request, actor
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
        me = actor.Actor(self.request.params['actor_id'], self.app.registry.get('config'))
        result = payments.process_card(
            actor=me,
            amount=self.request.params['amount'],
            plan=self.request.params.get('plan', 'monthly'),
            token=self.request.params['stripeToken']
        )
        if result:
            template = self.app.registry.get('template').get_template('stripe-form-success.html')
            template.globals['STATIC_PREFIX'] = '/static'
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
        else:
            template = self.app.registry.get('template').get_template('stripe-form-failure.html')
            template.globals['STATIC_PREFIX'] = '/static'
            self.response.write(template.render(self.obj.response.template_values).encode('utf-8'))
