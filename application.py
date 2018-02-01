import webapp2
import os
import logging
# import pydevd
from jinja2 import Environment, PackageLoader, select_autoescape

from aw_handlers import actor_root, actor_trust, devtests, actor_subscription, actor_callbacks, actor_resources
from aw_handlers import callback_oauth, actor_oauth
from aw_handlers import root_factory, actor_www, actor_properties, actor_meta, bots

app = webapp2.WSGIApplication([
    ('/', root_factory.RootFactory),
    webapp2.Route(r'/bot<:/?><path:(.*)>', bots.Bots),
    webapp2.Route(r'/oauth', callback_oauth.CallbackOauths),
    webapp2.Route(r'/<actor_id>/meta<:/?><path:(.*)>', actor_meta.ActorMeta),
    webapp2.Route(r'/<actor_id>/oauth<:/?><path:.*>', actor_oauth.ActorOauth),
    webapp2.Route(r'/<actor_id><:/?>', actor_root.ActorRoot),
    webapp2.Route(r'/<actor_id>/www<:/?><path:(.*)>', actor_www.ActorWWW),
    webapp2.Route(r'/<actor_id>/properties<:/?><name:(.*)>', actor_properties.ActorProperties),
    webapp2.Route(r'/<actor_id>/trust<:/?>', actor_trust.ActorTrust),
    webapp2.Route(r'/<actor_id>/trust/<relationship><:/?>', actor_trust.ActorTrustRelationships),
    webapp2.Route(r'/<actor_id>/trust/<relationship>/<peerid><:/?>', actor_trust.ActorTrustPeer),
    webapp2.Route(r'/<actor_id>/subscriptions<:/?>', actor_subscription.RootHandler),
    webapp2.Route(r'/<actor_id>/subscriptions/<peerid><:/?>', actor_subscription.RelationshipHandler),
    webapp2.Route(r'/<actor_id>/subscriptions/<peerid>/<subid><:/?>', actor_subscription.SubscriptionHandler),
    webapp2.Route(r'/<actor_id>/subscriptions/<peerid>/<subid>/<seqnr><:/?>', actor_subscription.DiffHandler),
    webapp2.Route(r'/<actor_id>/callbacks<:/?><name:(.*)>', actor_callbacks.ActorCallbacks),
    webapp2.Route(r'/<actor_id>/resources<:/?><name:(.*)>', actor_resources.ActorResources),
    webapp2.Route(r'/<actor_id>/devtest<:/?><path:(.*)>', devtests.Devtests),
], debug=True)


def set_config():
    if not app.registry.get('config'):
        myurl = os.getenv('APP_HOST_FQDN', "localhost")
        proto = os.getenv('APP_HOST_PROTOCOL', "https://")
        aw_type = "urn:actingweb:actingweb.org:spark-army-knife"
        bot_token = os.getenv('APP_BOT_TOKEN', "")
        bot_email = os.getenv('APP_BOT_EMAIL', "")
        bot_secret = os.getenv('APP_BOT_SECRET', "")
        bot_admin_room = os.getenv('APP_BOT_ADMIN_ROOM', "")
        oauth = {
            'client_id': os.getenv('APP_OAUTH_ID', ""),
            'client_secret': os.getenv('APP_OAUTH_KEY', ""),
            'redirect_uri': proto + myurl + "/oauth",
            'scope': "spark:people_read spark:rooms_read spark:rooms_write spark:memberships_read "
                     "spark:memberships_write spark:messages_write spark:messages_read spark:teams_read "
                     "spark:teams_write",
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
                'type': aw_type,
                'factory': proto + myurl + '/',
                'relationship': 'friend',  # associate, friend, partner, admin
            }
        }
        # Import the class lazily
        config = webapp2.import_string('actingweb.config')
        config = config.Config(
            database='dynamodb',
            fqdn=myurl,
            proto=proto,
            aw_type=aw_type,
            desc="Spark actor: ",
            version="2.0",
            devtest=True,
            actors=actors,
            force_email_prop_as_creator=True,
            unique_creator=True,
            default_relationship="associate",
            auto_accept_default_relationship=True,
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
            autoescape=True)
    return


def main():
    from paste import httpserver
    logging.debug('Starting up the Army Knife...')
    httpserver.serve(app, host='0.0.0.0', port='5000')


if __name__ == '__main__':
    # To debug in pycharm inside the Docker containter, remember to uncomment import pydevd as well
    # (and add to requirements.txt)
    # pydevd.settrace('docker.for.mac.localhost', port=3001, stdoutToServer=True, stderrToServer=True)

    set_config()
    set_template_env()
    main()
