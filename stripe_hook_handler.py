import webapp2
import json
import logging
from actingweb import aw_web_request, actor
from armyknife import payments
import stripe


# noinspection PyAttributeOutsideInit
class StripeHookHandler(webapp2.RequestHandler):

    def init(self):
        self.obj = aw_web_request.AWWebObj(
            url=self.request.url,
            params=self.request.params,
            body=self.request.body,
            headers=self.request.headers)

    def post(self):
        self.init()
        self.response.set_status(payments.process_webhook(
            self.request.body,
            self.request.headers['STRIPE_SIGNATURE'],
            self.app.registry.get('config')))
