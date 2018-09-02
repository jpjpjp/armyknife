import os
import datetime
import stripe
import pytz
import json
import logging
from .armyknife import ArmyKnife
from .ciscowebexteams import CiscoWebexTeams
from actingweb import actor

PLAN_NAME_MONTHLY = "plan_DT7JcRIIvbEIRh"
PLAN_NAME_YEARLY = "plan_DWYIIload0BMNa"
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_OOAQaJWTXVZo4KkWB99aWicUtFBg6a8e')

TRIAL_LENGTH = 30  # Number of days in trial length

PAID_FEATURES = [
    '/autoreply',
    '/todo',
    '/fu',
    '/followup'
    '/tom',
    '/topofmind',
    '/done',
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
TRIAL_FEATURES = PAID_FEATURES

stripe.log = 'info'
stripe.api_key = os.getenv('STRIPE_API_KEY', 'sk_test_IiAlGGLyqmEPPfqF4VY8Zn3w')


def check_subscriptions(cmd, store):
    # Check for trial and payment status
    perm_attrs = store.get_perm_attributes()
    trial = False
    abort = False
    msg = ''
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
    if 'data' in sub and 'sub_id' in sub['data']:
        now = datetime.datetime.now()
        end = datetime.datetime.fromtimestamp(sub['data']['sub_end'])
        if now < end:
            return True
    return False


def check_subscription_commands(cmd):
    return cmd in PAID_FEATURES


def check_trial_commands(cmd):
    return cmd in TRIAL_FEATURES


def get_subscribe_msg():
    return "Subscribe now!!!"


def process_card(actor=None, amount=None, token=None, plan='monthly'):
    if not actor or not amount or not token or not actor.id:
        return False
    store = ArmyKnife(actor.id, actor.config)
    attr = store.get_perm_attribute('subscription')
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
        if plan == 'yearly':
            plan_chosen = PLAN_NAME_YEARLY
        else:
            plan_chosen = PLAN_NAME_MONTHLY

        sub = stripe.Subscription.create(
            customer=cust['id'],
            items=[
                {
                    "plan": plan_chosen,
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
        payload = json.loads(payload)
        event = stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)
    except Exception:
        # Invalid payload or signature
        logging.error('Webhook signature verification error')
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
