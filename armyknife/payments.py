import os
import datetime
import stripe
import pytz

TRIAL_LENGTH = 30  # Number of days in trial length

PAID_FEATURES = [
    '/autoreply',
    '/todo',
    '/tom',
    '/topofmind',
    '/done',
    '/listroom'
]

# For now, just make all paid features available as trial features
TRIAL_FEATURES = PAID_FEATURES

stripe.log = 'debug'
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
    return True


def check_subscription_commands(cmd):
    return cmd in PAID_FEATURES


def check_trial_commands(cmd):
    return cmd in TRIAL_FEATURES


def get_subscribe_msg():
    return "Subscribe now!!!"


def process_card(actor_id=None, amount=None, token=None):
    if not actor_id or not amount or not token:
        return False

    return True