import webapp2
import os
#import pydevd
from jinja2 import Environment, PackageLoader, select_autoescape

from aw_handlers import actor_root, actor_trust, devtests, actor_subscription, actor_callbacks, actor_resources
from aw_handlers import callback_oauth, actor_oauth
from aw_handlers import root_factory, actor_www, actor_properties, actor_meta, bots

app = webapp2.WSGIApplication([
    ('/', root_factory.root_factory),
    webapp2.Route(r'/bot<:/?><path:(.*)>', bots.bots),
    (r'/(.*)/meta/?(.*)', actor_meta.actor_meta),
    webapp2.Route(r'/oauth', callback_oauth.callback_oauths),
    webapp2.Route(r'/<id>/oauth<:/?><path:.*>', actor_oauth.actor_oauth),
    webapp2.Route(r'/<id><:/?>', actor_root.actor_root),
    webapp2.Route(r'/<id>/www<:/?><path:(.*)>', actor_www.actor_www),
    webapp2.Route(r'/<id>/properties<:/?><name:(.*)>', actor_properties.actor_properties),
    webapp2.Route(r'/<id>/trust<:/?>', actor_trust.actor_trust),
    webapp2.Route(r'/<id>/trust/<relationship><:/?>', actor_trust.actor_trust_relationships),
    webapp2.Route(r'/<id>/trust/<relationship>/<peerid><:/?>', actor_trust.actor_trust_peer),
    webapp2.Route(r'/<id>/subscriptions<:/?>', actor_subscription.rootHandler),
    webapp2.Route(r'/<id>/subscriptions/<peerid><:/?>', actor_subscription.relationshipHandler),
    webapp2.Route(r'/<id>/subscriptions/<peerid>/<subid><:/?>', actor_subscription.subscriptionHandler),
    webapp2.Route(r'/<id>/subscriptions/<peerid>/<subid>/<seqnr><:/?>', actor_subscription.diffHandler),
    webapp2.Route(r'/<id>/callbacks<:/?><name:(.*)>', actor_callbacks.actor_callbacks),
    webapp2.Route(r'/<id>/resources<:/?><name:(.*)>', actor_resources.actor_resources),
    webapp2.Route(r'/<id>/devtest<:/?><path:(.*)>', devtests.devtests),
], debug=True)


def set_config():
    if not app.registry.get('config'):
        myurl = os.getenv('APP_HOST_FQDN', "localhost")
        proto = os.getenv('APP_HOST_PROTOCOL', "https://")
        type = "urn:actingweb:actingweb.org:spark-army-knife"
        bot_token = os.getenv('APP_BOT_TOKEN', "")
        bot_email = os.getenv('APP_BOT_EMAIL', "")
        bot_secret = os.getenv('APP_BOT_SECRET', "")
        bot_admin_room = os.getenv('APP_BOT_ADMIN_ROOM', "")
        oauth = {
            'client_id': os.getenv('APP_OAUTH_ID',""),
            'client_secret': os.getenv('APP_OAUTH_KEY',""),
            'redirect_uri': proto + myurl + "/oauth",
            'scope': "spark:people_read spark:rooms_read spark:rooms_write spark:memberships_read spark:memberships_write spark:messages_write spark:messages_read spark:teams_read spark:teams_write",
            'auth_uri': "https://api.ciscospark.com/v1/authorize",
            'token_uri': "https://api.ciscospark.com/v1/access_token",
            'response_type': "code",
            'grant_type': "authorization_code",
            'refresh_type': "refresh_token",
        }
        actors = {
            'boxbasic': {
                'type': 'urn:actingweb:actingweb.org:boxbasic',
                'factory': 'https://box-spark-dev.appspot.com/',
                'relationship': 'friend',
            },
            'myself': {
                'type': type,
                'factory': proto + myurl + '/',
                'relationship': 'friend',  # associate, friend, partner, admin
            }
        }
        # Import the class lazily
        config = webapp2.import_string('actingweb.config')
        config = config.config(
            database='dynamodb',
            fqdn=myurl,
            proto=proto,
            type=type,
            desc="Spark actor: ",
            version="2.0",
            devtest=True,
            actors=actors,
            force_email_prop_as_creator=True,
            unique_creator=True,
            www_auth="oauth",
            ui=True,
            bot={
                "token": bot_token,
                "email": bot_email,
                "secret": bot_secret,
                "admin_room": bot_admin_room
            },
            oauth=oauth
        )
        # Register the instance in the registry.
        app.registry['config'] = config
    return


def set_template_env():
    if not app.registry.get('template'):
        # Import the class lazily.
        webapp2.import_string('jinja2.Environment')
        # Register the instance in the registry.
        app.registry['template'] = Environment(
            loader=PackageLoader('application', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
    return


def main():
    from paste import httpserver
    httpserver.serve(app, host='0.0.0.0', port='5000')


if __name__ == '__main__':
    #To debug in pycharm inside the Docker containter, remember to uncomment import pydevd as well
    # (and add to requirements.txt)
    #pydevd.settrace('docker.for.mac.localhost', port=3001, stdoutToServer=True, stderrToServer=True)

    set_config()
    set_template_env()
    main()
