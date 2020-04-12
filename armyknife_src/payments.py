import os
import datetime
import stripe
import pytz
import json
import logging
from .armyknife import ArmyKnife
from .ciscowebexteams import CiscoWebexTeams
from actingweb import actor

PLAN_NAMES = {
    'monthly2.99': {
        'id': os.getenv('STRIPE_PLAN_MONTHLY_2.99', 'armyknife_support_monthly_2-99'),
        'amount': 2.99
    },
    'yearly29.99': {
        'id': os.getenv('STRIPE_PLAN_YEARLY_29.99', 'armyknife_support_yearly_29-99'),
        'amount': 29.99
    },
    'monthly3.99': {
        'id': os.getenv('STRIPE_PLAN_MONTHLY_3.99', 'armyknife_support_monthly_3-99'),
        'amount': 3.99
    },
    'yearly39.99': {
        'id': os.getenv('STRIPE_PLAN_YEARLY_39.99', 'armyknife_support_yearly_39-99'),
        'amount': 39.99
    },
    'yearly20': {
        'id': os.getenv('STRIPE_PLAN_YEARLY_20', 'armyknife_support_yearly_20'),
        'amount': 20.00
    }
    
}
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_OOAQaJWTXVZo4KkWB99aWicUtFBg6a8e')

TRIAL_LENGTH = 30  # Number of days in trial length

PAID_FEATURES_BOT = [
    '/autoreply',
    '/noautoreply',
    '/todo',
    '/fu',
    '/followup'
    '/tom',
    '/topofmind',
    '/done'
]

PAID_FEATURES_INT = [
    '/makepublic',
    '/makeprivate',
    '/boxfolder',
    '/noboxfolder',
    '/box',
    '/nobox',
    '/checkmember',
    '/deletewebhook',
    '/listwebhooks'
]

# For now, just make all paid features available as trial features
TRIAL_FEATURES = PAID_FEATURES_BOT + PAID_FEATURES_INT

stripe.log = 'info'
stripe.api_key = os.getenv('STRIPE_API_KEY', 'sk_test_IiAlGGLyqmEPPfqF4VY8Zn3w')

# Returns bool tuple of subscription, trial
def check_valid_trial_or_subscription(store):
    # Check for trial and payment status
    perm_attrs = store.get_perm_attributes()
    trial = False
    subscription = False
    # Does the user have a subscription?
    if 'subscription' not in perm_attrs:
        # If not, let's check if this is a trial
        if 'first_visit' not in perm_attrs:
            store.save_perm_attribute('first_visit', "today")
            trial = True
        else:
            if check_valid_trial(perm_attrs['first_visit']):
                trial = True
    subscription = check_valid_subscription(perm_attrs.get('subscription', None))
    return (subscription, trial)

def check_subscriptions(cmd, store, context='integration'):
    trial, subscription = check_valid_trial_or_subscription(store)
    abort = False
    msg = ''
    if trial and not subscription:
        if not check_trial_commands(cmd) and check_subscription_commands(cmd):
            msg = msg + "You are in the trial period and just used a command only available to subscribers!\n\n"
            msg = msg + get_subscribe_msg()
            abort = True
    elif not subscription:
        if check_subscription_commands(cmd):
            msg = msg + "Your trial has expired!\n\n"
            msg = msg + get_subscribe_msg()
            abort = True
    # Avoid that message is sent from both bot and integration
    if context == 'integration' and cmd not in PAID_FEATURES_INT:
        msg = ''
    if context == 'bot' and cmd not in PAID_FEATURES_BOT:
        msg = ''
    return abort, msg


def check_valid_trial(trial):
    now = datetime.datetime.utcnow()
    now = now.replace(tzinfo=pytz.utc)
    if trial['timestamp'] + datetime.timedelta(days=TRIAL_LENGTH) < now:
        return False
    return True


def check_valid_subscription(sub):
    if not sub:
        return False
    if 'data' in sub:
        now = datetime.datetime.now()
        end = datetime.datetime.fromtimestamp(sub['data']['sub_end'])
        if now < end:
            return True
    return False


def check_subscription_commands(cmd):
    return cmd in PAID_FEATURES_INT or cmd in PAID_FEATURES_BOT


def check_trial_commands(cmd):
    return cmd in TRIAL_FEATURES


def get_subscribe_msg():
    return "Subscribe now!!!"

def get_subscribe_md(actor=None, config=None):
    if not actor or not config:
        return {}
    my_stripe_url = config.root + 'stripe?id=' + actor.id
    return "The **ArmyKnife** costs money to operate, would you be willing to pay to support?\n\n" + \
           "* [Monthly $2.99](" + my_stripe_url + '&plan=monthly2.99' + ")\n\n" + \
           "* [Yearly $29.99](" + my_stripe_url + '&plan=yearly29.99' + ")\n\n" + \
           "* [Monthly $3.99](" + my_stripe_url + '&plan=monthly3.99' + ")\n\n" + \
           "* [Yearly $39.99](" + my_stripe_url + '&plan=yearly39.99' + ")\n\n" + \
           "* [Yearly $20](" + my_stripe_url + '&plan=yearly20' + ")\n\n" 

def get_subscribe_form(actor=None, config=None):
    if not actor or not config:
        return {}
    my_stripe_url = config.root + 'stripe?id=' + actor.id
    img_url = config.root + 'static/army_knife.png'
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.1",
        "body": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": 2,
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": "Help support the Army Knife!",
                                "weight": "Bolder",
                                "size": "Medium"
                            },
                            {
                                "type": "TextBlock",
                                "text": "The ArmyKnife costs money to operate, would you be willing to pay to support?",
                                "isSubtle": "true",
                                "wrap": "true"
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": 1,
                        "items": [
                            {
                                "type": "Image",
                                "url": img_url,
                                "size": "auto"
                            }
                        ]
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "$2.99 per month",
                "url": my_stripe_url + '&plan=monthly2.99'
            },
            {
                "type": "Action.OpenUrl",
                "title": "$29.99 per year",
                "url": my_stripe_url + '&plan=yearly29.99'
            },
            {
                "type": "Action.OpenUrl",
                "title": "$3.99 per month",
                "url": my_stripe_url + '&plan=monthly3.99'
            },
            {
                "type": "Action.OpenUrl",
                "title": "$39.99 per year",
                "url": my_stripe_url + '&plan=yearly39.99'
            },
            {
                "type": "Action.OpenUrl",
                "title": "$20 per year",
                "url": my_stripe_url + '&plan=yearly20'
            }
        ]
    }


def process_card(actor=None, token=None, plan='monthly2.99', config=None):
    if not actor  or not token or not actor.id:
        return False
    store = ArmyKnife(actor.id, actor.config)
    attr = store.get_perm_attribute('subscription')
    bot = CiscoWebexTeams(auth=None, actor_id=None, config=config)
    cust = {}
    if attr and 'data' in attr and 'stripe_id' in attr['data']:
        cust = stripe.Customer.retrieve(attr['data']['stripe_id'])
        cust.source = token
        cust.save()
        data = attr['data']
        data['card_id'] = cust['default_source']
        store.save_perm_attribute('subscription', data)
    else:
        try:
            cust = stripe.Customer.create(
                email=actor.creator,
                description=actor.id,
                source=token
            )
        except Exception as e:
            logging.error('Card did not verify for ' + actor.id)
            return False
        if cust and 'id' in cust:
            data = {
                'stripe_id': cust['id'],
                'card_id': cust['default_source']
            }
            store.save_perm_attribute('subscription', data)
        else:
            logging.error('Failed to create or retrieve customer on ' + actor.id)
            return False
    if 'subscriptions' in cust and cust['subscriptions']['total_count'] == 0:
        plan_chosen = PLAN_NAMES[plan]

        sub = stripe.Subscription.create(
            customer=cust['id'],
            items=[
                {
                    "plan": plan_chosen['id'],
                },
            ]
        )
        if sub and 'id' in sub and 'current_period_start' in sub and 'current_period_end' in sub:
            data['sub_id'] = sub['id']
            data['sub_start'] = sub['current_period_start']
            data['sub_end'] = sub['current_period_end']
        else:
            logging.error('Failed to create new subscription '  + actor.id)
            return False
        bot.post_admin_message(
            text="Subscription for user " + actor.creator + " was just created with plan " + plan + ".\n\n",
            markdown=True
        )
        store.save_perm_attribute('subscription', data)
    else:
        logging.warn('Updated card. Subscription already exists on ' + actor.id)
    return True


def cancel_subscription(actor=None, config=None):
    if not actor or not actor.id or not actor.creator or not config:
        return False
    store = ArmyKnife(actor.id, actor.config)
    attr = store.get_perm_attribute('subscription')
    bot = CiscoWebexTeams(auth=None, actor_id=None, config=config)
    if attr and 'data' in attr and 'sub_id' in attr['data']:
        try:
            sub = stripe.Subscription.retrieve(attr['data']['sub_id'])
            sub.delete()
        except Exception as e:
            if hasattr(e, 'http_status') and e.http_status != 404:
                bot.post_bot_message(
                    email=actor.creator,
                    text="Something failed when cancelling your subscription. Please use `/support` to contact support.",
                    markdown=True
                )
            else:
                bot.post_bot_message(
                    email=actor.creator,
                    text="Your subscription has already been deleted.",
                    markdown=True
                )
            del attr['data']['sub_id']
            store.save_perm_attribute('subscription', attr['data'])
            return False
        bot.post_bot_message(
            email=actor.creator,
            text="Your subscription was successfully cancelled.",
            markdown=True
        )
        bot.post_admin_message(
            text="Subscription for user " + actor.creator + " was just cancelled.\n\n",
            markdown=True
        )
        del attr['data']['sub_id']
        store.save_perm_attribute('subscription', attr['data'])
        return True
    bot.post_bot_message(
        email=actor.creator,
        text="You don't have an active subscription.",
        markdown=True
    )
    return False


def process_webhook(payload, signature, config):
    try:
        event = stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)
    except Exception:
        # Invalid payload or signature
        logging.error('Webhook signature verification error')
        return 400
    try: 
        payload = json.loads(payload)
        logging.error('Stripe webhook json decode error')
    except:
        return 400
    cust = None
    bot = CiscoWebexTeams(auth=None, actor_id=None, config=config)
    if 'invoice.' in payload['type']:
        try:
            cust = stripe.Customer.retrieve(payload['data']['object']['customer'])
            actor_id = cust.get('description', None)
            if not actor_id:
                return 204
        except:
            # Not possible to know who this event belongs to
            bot.post_admin_message(
                text="Got a Stripe webhook where no actor could be found: " + payload['data']['object']['customer'],
                markdown=True
            )
            return 204
        store = ArmyKnife(actor_id, config)
        user = actor.Actor(actor_id, config)
        attr = store.get_perm_attribute('subscription')
        if 'invoice.payment_succeeded' in payload['type']:
            # Notify admin, update subscription end time
            if 'data' in payload and 'object' in payload['data'] and 'subscription' in payload['data']['object']:
                sub = payload['data']['object']
                amount = sub.get('amount_paid', 0)
                if attr and 'data' in attr:
                    data = attr['data']
                else:
                    data = {}
                if 'sub_id' not in data:
                    data['sub_id'] = sub['subscription']
                if data['sub_id'] == sub['subscription']:
                    if data['sub_start'] < sub['period_start']:
                        data['sub_start'] = sub['period_start']
                    if data['sub_end'] < sub['period_end']:
                        data['sub_end'] = sub['period_end']
                else:
                    bot.post_admin_message(
                        text="Got wrong subscription id for this user: " + sub['subscription'],
                        markdown=True
                    )
                store.save_perm_attribute('subscription', data)
                bot.post_admin_message(
                    text="Payment of $" + str(amount/100.0) + " received from " + user.creator
                         # + "\n\n```\n\n" + json.dumps(payload, sort_keys=True, indent=4) + "\n\n```\n\n"
                    , markdown=True
                )
        elif 'invoice.payment_failed' in payload['type']:
            # Notify admin and user
            bot.post_bot_message(
                email=actor.creator,
                text="Your subscription payment failed. Please do `/subscription` and update your card!",
                markdown=True
            )
            bot.post_admin_message(
                text="Payment failed for " + actor.creator,
                markdown=True
            )
            pass
        elif 'invoice.upcoming' in payload['type']:
            # Do nothing for now
            pass
    elif 'customer.source' in payload['type']:
        if 'customer.source.expiring' in payload['type']:
            # Notify user and share link to update card
            bot.post_bot_message(
                email=actor.creator,
                text="Your card will soon expire. Please do `/subscription` and update your card!",
                markdown=True
            )
        elif 'customer.source.updated' in payload['type']:
            # Notify user on successful updated card
            bot.post_bot_message(
                email=actor.creator,
                text="Your card was successfully updated. Thanks!",
                markdown=True
            )
    return 200
