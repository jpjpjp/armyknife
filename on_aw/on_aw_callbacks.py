#!/usr/bin/env python
#
from actingweb import actor
from actingweb import auth as auth_class
from actingweb import config
from actingweb import aw_proxy
from spark import ciscospark
from google.appengine.ext import deferred

import logging
import json
import os
import re
import base64
import datetime
import time
import hmac
import hashlib
from google.appengine.ext.webapp import template
import on_aw_delete


__all__ = [
    'on_post_callbacks',
    'on_get_callbacks',
    'on_post_subscriptions',
    'on_delete_callbacks',
]


def check_member(mail, target, spark):
    out = ""
    next_rooms = spark.getRooms()
    rooms = []
    while next_rooms and 'items' in next_rooms:
        rooms.extend(next_rooms['items'])
        next_rooms = spark.getRooms(get_next=True)
    if len(rooms) > 0:
        out += "**You are member of " + str(len(rooms)) + " group rooms**\n\n"
        out += "Searching for rooms with " + target + " as a member...\n\n"
    else:
        out += "**No rooms found**"
    spark.postBotMessage(
        email=mail,
        text=out,
        markdown=True)
    out = ""
    nr_of_rooms = 0
    found_in_rooms = 0
    for r in rooms:
        next_members = spark.getMemberships(id=str(r['id']))
        nr_of_rooms += 1
        members = []
        while next_members and 'items' in next_members:
            members.extend(next_members['items'])
            next_members = spark.getMemberships(get_next=True)
        if len(members) > 0:
            for r in members:
                if ('@' in target and 'personEmail' in r and target in r['personEmail'].lower()) or ('@' not in target and 'personDisplayName' in r and target in r['personDisplayName'].lower()):
                    found_in_rooms += 1
                    room = spark.getRoom(id=str(r['roomId']))
                    if room and 'title' in room:
                        out += room['title'] + " (" + r['roomId'] + ")"
                    else:
                        out += "Unknown title (" + r['roomId'] + ")"
                    out += "\n"
                    if len(out) > 2000:
                        spark.postBotMessage(
                            email=mail,
                            text=out)
                        out = ""
                    break
    if len(out) > 0:
        spark.postBotMessage(
            email=mail,
            text=out)
    spark.postBotMessage(
        email=mail,
        text="----\n\nSearched " + str(nr_of_rooms) + " rooms, and found " + target + " in " + str(found_in_rooms) + " rooms.",
        markdown=True)

def on_get_callbacks(myself, req, auth, name):
    spark = ciscospark.ciscospark(auth, myself.id)
    if name == 'joinroom':
        uuid = req.request.get('id')
        room = spark.loadRoomByUuid(uuid)
        if not room:
            req.response.set_status(404)
            return True
        template_values = {
            'id': uuid,
            'title': room.title,
        }
        template_path = os.path.join(os.path.dirname(__file__), '../templates/spark-joinroom.html')
        req.response.write(template.render(template_path, template_values).encode('utf-8'))
    if name == 'makefilepublic':
        pass
        # This is not secure!!! So do not execute
        # token is exposed directly in javascript in the users browser

        #template_values = {
        #    'url': str(req.request.get('url')),
        #    'token': str(auth.token),
        #    'filename': str(req.request.get('filename')),
        #}
        #template_path = os.path.join(os.path.dirname(__file__), '../templates/spark-getattachment.html')
        #req.response.write(template.render(template_path, template_values).encode('utf-8')) 
    return True


def on_delete_callbacks(myself, req, auth, name):
    """Customizible function to handle DELETE /callbacks"""
    # return True if callback has been processed
    return False


def on_post_callbacks(myself, req, auth, name):
    Config = config.config()
    spark = ciscospark.ciscospark(auth, myself.id)
    logging.debug("Callback body: " + req.request.body.decode('utf-8', 'ignore'))
    chatRoomId = myself.getProperty('chatRoomId').value
    # Clean up any actor creations from earlier where we got wrong creator email
    if myself.creator == Config.bot['email'] or myself.creator == "creator":
        my_email = myself.getProperty('email').value
        if my_email and len(my_email) > 0:
            myself.modify(creator=my_email)
    # Deprecated support for /callbacks/room
    if name == 'room':
        req.response.set_status(404)
        return True
    # non-json POSTs to be handled first
    if name == 'joinroom':
        uuid = req.request.get('id')
        email = req.request.get('email')
        room = spark.loadRoomByUuid(uuid)
        template_values = {
            'title': room.title,
        }
        if not spark.addMember(id=room.id, email=email):
            spark.postBotMessage(
                email=myself.creator,
                text="Failed adding new member " +
                email + " to room " + room.title)
            template_path = os.path.join(os.path.dirname(
                __file__), '../templates/spark-joinedroom-failed.html')
        else:
            spark.postBotMessage(
                email=myself.creator,
                text="Added new member " + email + " to room " + room.title)
            template_path = os.path.join(os.path.dirname(
                __file__), '../templates/spark-joinedroom.html')
        req.response.write(template.render(template_path, template_values).encode('utf-8'))
        return True
    # Handle json POSTs below
    body = json.loads(req.request.body.decode('utf-8', 'ignore'))
    data = body['data']
    if 'roomId' in data:
        responseRoomId = data['roomId']
    else:
        responseRoomId = chatRoomId
    now = datetime.datetime.now()
    myOauthId = myself.getProperty('oauthId').value
    if myself.getProperty('autoreplyMsg').value:
        reply_msg = "Via armyknife@sparkbot.io auto-reply:\n\n" + myself.getProperty('autoreplyMsg').value
    else:
        reply_msg = None
    service_status = myself.getProperty('service_status').value
    if not service_status:
        myself.setProperty('service_status', 'firehose')
    # validateOAuthToken() returns the redirect URL if token cannot be refreshed
    if len(auth.validateOAuthToken(lazy=True)) > 0:
        if not service_status or service_status != 'invalid':
            myself.setProperty('service_status', 'invalid')
        logging.info("Was not able to automatically refresh token.")
        token_invalid = myself.getProperty('token_invalid').value
        if not token_invalid or token_invalid != now.strftime("%Y%m%d"):
            myself.setProperty('token_invalid', now.strftime("%Y%m%d"))
            spark.postBotMessage(
                email=myself.creator,
                text="Your Spark Army Knife account has no longer access. Please type "\
                "/init in this room to re-authorize the account.")
            spark.postBotMessage(
                email=myself.creator,
                text="If you repeatedly get this error message, do /delete DELETENOW "\
                "before a new /init. This will reset your account (note: all settings as well).")
            logging.info("User (" + myself.creator + ") has invalid refresh token and got notified.")
        req.response.set_status(202, "Accepted, but not processed")
        return True
    # This is a special section that uses firehose for all messages to retrieve pinned messages
    # to see if anything needs to be processed (for other actors than the one receiving the firehose)
    due = spark.getDuePinnedMessages()
    for m in due:
        pin_owner = actor.actor(id=m.actorId)
        auth2 = auth_class.auth(id=m.actorId)
        spark2 = ciscospark.ciscospark(auth=auth2, actorId=m.actorId)
        email_owner = pin_owner.getProperty(name='email').value
        if len(m.comment) == 0:
            m.comment = "ARMY KNIFE REMINDER"
        if m.id and len(m.id) > 0:
            pin = spark2.getMessage(id=m.id)
            if not pin:
                logging.warn('Not able to retrieve message data for pinned message')
                spark2.postBotMessage(
                    email=email_owner,
                    text="You had a pinned reminder, but it was not possible to retrieve details."
                )
                continue
            person = spark2.getPerson(id=pin['personId'])
            room = spark2.getRoom(id=pin['roomId'])
            if not person or not room:
                logging.warn('Not able to retrieve person and room data for pinned message')
                spark2.postBotMessage(
                    email=email_owner,
                    text="You had a pinned reminder, but it was not possible to retrieve details."
                )
                continue
            spark2.postBotMessage(
                email=email_owner,
                text="**PIN ALERT!! - " + m.comment + "**\n\n"\
                "From " + person['displayName'] + " (" + person['emails'][0] + ")" + " in room (" + room['title'] + ")\n\n" +
                pin['text'] + "\n\n",
                markdown=True)
        else:
            if m.comment == '#/TOPOFMIND':
                topofmind = pin_owner.getProperty('topofmind').value
                if topofmind:
                    try:
                        topofmind = json.loads(topofmind)
                        toplist = topofmind['list']
                    except:
                        toplist = {}
                else:
                    toplist = None
                if toplist:
                    out = "**Your Daily Top of Mind Reminder**"
                    modified = pin_owner.getProperty('topofmind_modified').value
                    if modified:
                        timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                        out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                    out += "\n\n---\n\n"
                    for i, el in sorted(toplist.items()):
                        out = out + "**" + i + "**: " + el + "\n\n"
                    spark2.postBotMessage(
                        email=email_owner,
                        text=out,
                        markdown=True)
                spark2.deletePinnedMessages(comment="#/TOPOFMIND")
                targettime = m.timestamp + datetime.timedelta(days=1)
                spark2.savePinnedMessage(comment='#/TOPOFMIND', timestamp=targettime)
            else:
                spark2.postBotMessage(
                    email=email_owner,
                    text="**PIN ALERT!! - " + m.comment + "**",
                    markdown=True)
    if 'X-Spark-Signature' in req.request.headers:
        sign = req.request.headers['X-Spark-Signature']
    else:
        sign = None
    if sign and len(sign) > 0:
        myhash = hashlib.sha256()
        myhash.update(myself.passphrase)
        msghash = hmac.new(myhash.hexdigest(), req.request.body, digestmod=hashlib.sha1)
        if msghash.hexdigest() == sign:
            logging.debug('Signature matches')
        else:
            logging.debug('Signature does not match ' + str(sign))
            sign = None
    if not sign:
         # This code is temporary to re-register all webhooks with a secret
         # Once all accounts have been re-registered, the message should just be
         # dropped here.
        if '@cisco.com' in myself.creator:
            req.response.set_status(403, "Forbidden")
            return True
        logging.debug("Didn't get message signature from Spark, re-registering firehose...")
        firehoseId = myself.getProperty('firehoseId')
        if firehoseId and firehoseId.value:
            spark.unregisterWebHook(firehoseId.value)
        msghash = hashlib.sha256()
        msghash.update(myself.passphrase)
        hook = spark.registerWebHook(name='Firehose', target=Config.root + myself.id + '/callbacks/firehose', 
            resource='all', event='all', secret=msghash.hexdigest())
        if hook and hook['id']:
            logging.debug('Successfully registered secured firehose webhook')
            spark.postAdminMessage(text='Successfully registered secured firehose: ' + myself.creator)
            myself.setProperty('firehoseId', hook['id'])
        else:
            logging.debug('Failed to register messages firehose webhook')
        # Do not accept this message as it may be an attacker
        req.response.set_status(403, "Forbidden")
        return True
    if name == 'firehose':
        if body['resource'] == 'messages':
            if body['event'] == 'created':
                # Ignore all messages from sparkbots
                if "@sparkbot.io" in data['personEmail'].lower():
                    req.response.set_status(204)
                    return True
                if data['roomType'] == 'direct' and reply_msg and data['personEmail'] != myself.creator:
                    # Retrieve the last user we responded to and don't reply if it's the same user
                    lastAutoReply = myself.getProperty('autoreplyMsg-last').value
                    if lastAutoReply and lastAutoReply == data['personEmail'].lower():
                        req.response.set_status(204)
                        return True
                    else:
                        myself.setProperty('autoreplyMsg-last', data['personEmail'].lower())
                    msg = spark.getMessage(data['id'])
                    if not msg or 'text' not in msg:
                        myself.setProperty('service_status', 'invalid')
                        lastErr = spark.lastResponse()
                        logging.warn(
                            "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                            ") - " + lastErr['message'])
                        return False
                    if "armyknife@sparkbot.io" in msg['text']:
                        req.response.set_status(204)
                        return True
                    personSender = spark.getPerson(id=data['personId'])
                    spark.postMessage(
                        data['roomId'], reply_msg, markdown=True)
                    if 'displayName' not in personSender:
                        personSender = {}
                        personSender['displayName'] = "Unknown name"
                    spark.postBotMessage(email=myself.creator,
                                         text="**" + personSender['displayName'] + " (" +
                                         data['personEmail'] +
                                         ") sent a 1:1 message to you (auto-replied to) " +
                                         ":**\n\n" +
                                         msg['text'], markdown=True)
                    reply_msg = None
                    req.response.set_status(204)
                    return True
                mentioned = False
                if 'mentionedPeople' in data:
                    for person in data['mentionedPeople']:
                        if person == myOauthId:
                            mentioned = True
                            if reply_msg:
                                spark.postMessage(
                                    data['roomId'], reply_msg, markdown=True)
                                reply_on = '(auto-replied to)'
                            else:
                                reply_on = ''
                            room = spark.getRoom(data['roomId'])
                            msg = spark.getMessage(data['id'])
                            personMentioning = spark.getPerson(id=data['personId'])
                            if not room or not msg or not personMentioning:
                                myself.setProperty('service_status', 'invalid')
                                lastErr = spark.lastResponse()
                                logging.warn(
                                    "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                                    ") - " + lastErr['message'])
                                return False
                            if 'title' in room and 'text' in msg:
                                no_alert = myself.getProperty('no_mentions').value
                                if not no_alert or no_alert.lower() != 'true':
                                    spark.postBotMessage(email=myself.creator,
                                                         text="**" + personMentioning['displayName'] + " (" +
                                                         data['personEmail'] +
                                                         ") mentioned you " + reply_on + " in the room " +
                                                         room['title'] + ":**\n\n" +
                                                         msg['text'], markdown=True)
                if (data['roomType'] == 'direct' or mentioned) and data['personEmail'] != myself.creator:
                    msg = spark.getMessage(data['id'])
                    if not msg or 'text' not in msg:
                        myself.setProperty('service_status', 'invalid')
                        lastErr = spark.lastResponse()
                        logging.warn(
                            "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
                            ") - " + lastErr['message'])
                        return False
                    if not service_status or service_status == 'invalid' or service_status == 'firehose':
                        myself.setProperty('service_status', 'active')
                    me = spark.getMe()
                    message = msg['text']
                    if 'displayName' in me:
                        userName = me['displayName']
                        if mentioned:
                            message = msg['text'][len(userName)+1:]
                            logging.debug('-'+message+'-')
                    else:
                        userName = 'No Name Available'
                    tokens = message.split(' ')
                    if tokens[0] == '/topofmind' or tokens[0] == '/tom':
                        topofmind = myself.getProperty('topofmind').value
                        toplist = None
                        if topofmind:
                            try:
                                topofmind = json.loads(topofmind)
                                toplist = topofmind['list']
                            except:
                                toplist = None
                        if len(tokens) == 1:
                            if toplist and len(toplist) > 0:
                                out = "**" + topofmind['title'] + " for " + userName + "**"
                                modified = myself.getProperty('topofmind_modified').value
                                if modified:
                                    timestamp = datetime.datetime.strptime(modified, "%Y-%m-%d %H:%M")
                                    out += " `(last edited: " + timestamp.strftime('%Y-%m-%d %H:%M') + " UTC)`\n\n"
                                out += "\n\n---\n\n"
                                for i, el in sorted(toplist.items()):
                                    out = out + "**" + i + "**: " + el + "\n\n"
                                spark.postBotMessage(
                                    email=data['personEmail'],
                                    text=out,
                                    markdown=True)
                            else:
                                spark.postBotMessage(
                                    email=data['personEmail'],
                                    text="No available top of mind list",
                                    markdown=True)
                                toplist = None
                        elif len(tokens) == 2 and tokens[1].lower() == 'subscribe':
                            # myself is now the owner of the topofmind
                            # data['personEmail'] is the person wanting to subscribe
                            subscriber_email = data['personEmail']
                            subscriber = actor.actor()
                            subscriber.get_from_property(name='email', value=subscriber_email)
                            if not subscriber.id:
                                spark.postBotMessage(
                                    email=subscriber_email,
                                    text="Failed in looking up your Spark Army Knife account. Please type /init here"
                                         " and authorize Spark Army Knife.")
                                req.response.set_status(204)
                                return True
                            peerid = myself.id
                            logging.debug("Looking for existing peer trust:(" + str(peerid) + ")")
                            trust = subscriber.getTrustRelationship(peerid=peerid)
                            if not trust:
                                trust = subscriber.createReciprocalTrust(
                                    url=Config.actors['myself']['factory']+str(peerid), secret=Config.newToken(), 
                                    desc="Top of mind subscriber", relationship="associate",
                                    type=Config.type)
                                if trust:
                                    spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Created trust relationship for top of mind subscription.")
                            else:
                                spark.postBotMessage(
                                    email=subscriber_email,
                                    text="Trust relationship for top of mind subscription was already established.")
                            if not trust:
                                spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Creation of trust relationship for top of mind subscription failed.\n\n"
                                             "Cannot create subscrition.")
                            else:
                                sub = subscriber.getSubscriptions(peerid=trust['peerid'], target='properties',
                                                                  subtarget='topofmind', callback=True)
                                if len(sub) > 0:
                                    spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Top of mind subscription was already created.")
                                else:
                                    sub = subscriber.createRemoteSubscription(peerid=trust['peerid'], target='properties',
                                                                              subtarget='topofmind', granularity='high')
                                    if not sub:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Creation of new top of mind subscription failed.")
                                    else:
                                        spark.postBotMessage(
                                            email=subscriber_email,
                                            text="Created top of mind subscription for " + myself.creator + ".")
                        elif len(tokens) == 2 and tokens[1].lower() == 'unsubscribe':
                            # myself is now the owner of the topofmind
                            # data['personEmail'] is the person wanting to unsubscribe
                            subscriber_email = data['personEmail']
                            subscriber = actor.actor()
                            subscriber.get_from_property(name='email', value=subscriber_email)
                            if not subscriber.id:
                                spark.postBotMessage(
                                    email=subscriber_email,
                                    text="Failed in looking up your Spark Army Knife account.")
                                req.response.set_status(204)
                                return True
                            # My subscriptions
                            subs = subscriber.getSubscriptions(
                                peerid=myself.id,
                                target='properties',
                                subtarget='topofmind',
                                callback=True)
                            if len(subs) >= 1:
                                if not subscriber.deleteRemoteSubscription(peerid=myself.id, subid=subs[0]['subscriptionid']):
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Failed cancelling the top of mind subscription on your peer.")
                                elif not subscriber.deleteSubscription(peerid=myself.id, subid=subs[0]['subscriptionid']):
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Failed cancelling your top of mind subscription.")
                                else:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Cancelled the top of mind subscription.")
                            # Subscriptions on me
                            subs2 = subscriber.getSubscriptions(
                                peerid=myself.id,
                                target='properties',
                                subtarget='topofmind',
                                callback=False)
                            if len(subs2) == 0:
                                if not subscriber.deleteReciprocalTrust(peerid=myself.id, deletePeer=True):
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Failed cancelling the trust relationship.")
                                else:
                                    spark.postBotMessage(
                                        email=subscriber_email,
                                        text="Deleted the trust relationship.")
        if body['resource'] == 'memberships':
            if body['event'] == 'created' and ('personEmail' in data and data['personEmail'] == myself.creator):
                room = spark.getRoom(data['roomId'])
                if room and 'title' in room:
                    no_alert = myself.getProperty('no_newrooms').value
                    if not no_alert or no_alert.lower() != 'true':
                        spark.postBotMessage(email=myself.creator,
                                             text="You were added to the room " + room['title'])
                req.response.set_status(204)
                return True
            room = spark.loadRoom(data['roomId'])
            if room and room.boxFolderId:
                box = myself.getPeerTrustee(shorttype='boxbasic')
                proxy = aw_proxy.aw_proxy(peer_target=box)
                if body['event'] == 'created':
                    params = {
                        'collaborations': [
                                {
                                    'email': data['personEmail'],
                                },
                         ],
                        }
                elif body['event'] == 'deleted':
                    params = {
                        'collaborations': [
                                {
                                    'email': data['personEmail'],
                                    'action': 'delete',
                                },
                            ],
                        }
                proxy.changeResource(path='resources/folders/' + room.boxFolderId, params=params)
                if proxy.last_response_code < 200 or proxy.last_response_code > 299:
                    logging.warn('Unable to add/remove collaborator(' + data['personEmail'] +
                                 ') to Box folder(' + room.boxFolderId + ')')
                else:
                    logging.debug('Added/removed collaborator(' + data['personEmail'] +
                                  ') to Box folder(' + room.boxFolderId + ')')
    # Below here we only handle messages:created events, so don't process anything else
    if body['resource'] != 'messages' or body['event'] != 'created':
        req.response.set_status(204)
        return True
    spark.processMessage(data)
    # This is not a message from myself
    if data['personId'] != myOauthId:
        req.response.set_status(204)
        return True
    msg = spark.getMessage(data['id'])
    if not msg or 'text' not in msg:
        myself.setProperty('service_status', 'invalid')
        lastErr = spark.lastResponse()
        logging.warn(
            "Error in getting direct message from spark callback. Code(" + str(lastErr['code']) +
            ") - " + lastErr['message'])
        return False
    if not service_status or service_status == 'invalid' or service_status == 'firehose':
        myself.setProperty('service_status', 'active')
    msg_list = msg['text'].lower().split(" ")
    msg_list_wcap = msg['text'].split(" ")
    if msg_list[0] == '/pin':
        spark.deleteMessage(data['id'])
        if len(msg_list) >= 2:
            try:
                nr = int(msg_list[1]) - 1
            except:
                spark.postMessage(
                    id=responseRoomId,
                    text="In `/pin x +a[m|h|d|w] Your message`, x and a must be digits, using 1 for x.",
                    markdown=True)
                nr = 0
            if nr < 0:
                # Typed in 0 means no message
                nr = None
        else:
            nr = 0
        if nr > 10:
            max = nr+1
        else:
            max = 10
        targettime = None
        comment = None
        if len(msg_list) > 2:
            if len(msg_list) > 3:
                comment = msg['text'][len(msg_list[0])+len(msg_list[1])+len(msg_list[2])+3:]
            if '+' in msg_list[2]:
                deltalist = re.split('[m|h|d[w]', msg_list[2][1:])
                if deltalist:
                    delta = int(deltalist[0])
                else:
                    delta = 1
                typelist = re.split('\d+', msg_list[2])
                if deltalist and len(deltalist) == 2:
                    deltatype = typelist[1]
                else:
                    deltatype = 'd'
            else:
                spark.postMessage(
                    id=responseRoomId,
                    text="Usage: `/pin x +a[m|h|d|w] Your message`, e.g. /pin 3 +2h, where m = minutes, h = hours, d = days, w = weeks"\
                    "       Use x=0 to set a reminder with no reference to a message, e.g. `/pin 0 +2h Time to leave!`",
                    markdown=True)
                req.response.set_status(204)
                return True
            now = datetime.datetime.utcnow()
            if deltatype == 'm':
                targettime = now + datetime.timedelta(minutes=delta)
            elif deltatype == 'h':
                targettime = now + datetime.timedelta(hours=delta)
            elif deltatype == 'w':
                targettime = now + datetime.timedelta(days=(delta*7))
            else:
                targettime = now + datetime.timedelta(days=delta)
        if nr is not None:
            msgs = spark.getMessages(roomId=responseRoomId, beforeId=data['id'], max=max)
        if targettime:
            if nr is not None:
                spark.savePinnedMessage(id=msgs[nr]['id'], comment=comment, timestamp=targettime)
            else:
                spark.savePinnedMessage(comment=comment, timestamp=targettime)
        elif nr is not None:
            spark.postBotMessage(
                email=myself.creator,
                text="**Pinned (" + msgs[nr]['created'] + ") from " +
                msgs[nr]['personEmail'] + ":** " + msgs[nr]['text'],
                markdown=True)
    elif msg_list[0] == '/makepublic' and responseRoomId != chatRoomId:
        uuid = spark.addUUID2room(responseRoomId)
        if not uuid:
            spark.postMessage(
                id=responseRoomId,
                text="Failed to make room public")
        else:
            spark.postMessage(
                id=responseRoomId, text="Public URI: " + Config.root +
                myself.id + '/callbacks/joinroom?id=' + uuid)
    elif msg_list[0] == '/makeprivate' and responseRoomId != chatRoomId:
        if not spark.deleteFromRoom(responseRoomId, uuid=True):
            spark.postMessage(
                id=responseRoomId,
                text="Failed to make room private.")
        else:
            spark.postMessage(
                id=responseRoomId,
                text="Made room private and add URL will not work anymore.")
    elif msg_list[0] == '/listroom' and responseRoomId != chatRoomId:
        spark.deleteMessage(data['id'])
        room = spark.getRoom(id=responseRoomId)
        msg = ''
        for key in room:
            msg = msg + "**" + str(key) + "**: " + str(room[key]) + "\n\n"
            if key == 'id':
                id2 = base64.b64decode(room[key]).split("ROOM/")
                if len(id2) >= 2:
                    msg = msg + "**Web URL**:" + " https://web.ciscospark.com/rooms/" + id2[1] + "\n\n"
        if len(msg) > 0:
            spark.postBotMessage(
                email=myself.creator,
                text="**Room Details**\n\n" + msg +
                "\n\nUse `/listmembers` and `/listfiles` to get other room details.",
                markdown=True)
    elif msg_list[0] == '/listfiles' and responseRoomId != chatRoomId:
        spark.deleteMessage(data['id'])
        feature_toggles = myself.getProperty('featureToggles').value
        msgs = spark.getMessages(roomId=responseRoomId, max=200)
        room = spark.getRoom(id=responseRoomId)
        if 'title' in room:
            spark.postBotMessage(
                email=myself.creator,
                text="**Files in room: " + room['title'] + "**\n\n",
                markdown=True)
        while msgs:
            for msg in msgs:
                if 'files' in msg:
                    for file in msg['files']:
                        details = spark.getAttachmentDetails(file)
                        filename = re.search(ur"filename[^;\n=]*=(['\"])*(?:utf-8\'\')?(.*)(?(1)\1|)",
                                             details['Content-Disposition']).group(2)
                        timestamp = datetime.datetime.strptime(msg['created'],  "%Y-%m-%dT%H:%M:%S.%fZ")
                        time = timestamp.strftime('%Y-%m-%d %H:%M')
                        size = int(details['Content-Length'])/1024
                        if feature_toggles and ('listfiles' in feature_toggles or 'beta' in feature_toggles):
                            spark.postBotMessage(
                                email=myself.creator,
                                text=time + ": [" + filename + " (" + str(size) + " KB)](" + Config.root +
                                myself.id + '/www/getattachment?url=' + file + "&filename=" + filename + ")",
                                markdown=True)
                        else:
                            spark.postBotMessage(
                                email=myself.creator,
                                text=time + ": " + filename + " (" + str(size) + " KB)",
                                markdown=True)
            # Using max=0 gives us the next batch
            msgs = spark.getMessages(roomId=responseRoomId, max=0)
    elif msg_list[0] == '/listwebhooks' and responseRoomId == chatRoomId:
        spark.postBotMessage(
            email=myself.creator,
            text="**All Registered Webhooks on Your Account**\n\n- - -",
            markdown=True)
        ret = spark.getAllWebHooks()
        while 1:
            if not ret:
                break
            for h in ret['webhooks']:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**Name(id)**: " + h['name'] + " (" + h['id'] + ")"
                    "\n\n**Events**: " + h['resource'] + ":" + h['event'] +
                    "\n\n**Target**: " + h['targetUrl'] +
                    "\n\n**Created**: " + h['created'] +
                    "\n\n- - -\n\n",
                    markdown=True
                    )
            if not ret['next']:
                break
            ret = spark.getAllWebHooks(uri=ret['next'])
    elif msg_list[0] == '/deletewebhook' and responseRoomId == chatRoomId:
        if len(msg_list) != 2:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage `/deletewebook <webhookid>`.\n\nUse /listwebhooks to get the id."
            )
        else:
            hookId = msg_list_wcap[1]
            ret = spark.unregisterWebHook(id=hookId)
            if ret is not None:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Deleted webhook: " + hookId
                )
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Was not able to delete webhook: " + hookId
                )
    elif msg_list[0] == '/cleanwebhooks' and responseRoomId == chatRoomId:
        deferred.defer(spark.cleanAllWebhooks, id=responseRoomId)
        spark.postBotMessage(
            email=myself.creator,
            text="Started cleaning up ALL webhooks.")
        hook = spark.registerWebHook(
            name='Firehose',
            target=Config.root + myself.id + '/callbacks/firehose',
            resource='all',
            event='all')
        if hook and hook['id']:
            logging.debug('Successfully registered messages firehose webhook')
            myself.setProperty('firehoseId', hook['id'])
    elif msg_list[0] == '/countrooms' and responseRoomId == chatRoomId:
        out = "**Counting rooms...**\n\n----\n\n"
        next_rooms = spark.getRooms()
        rooms = []
        while next_rooms and 'items' in next_rooms:
            rooms.extend(next_rooms['items'])
            next_rooms = spark.getRooms(get_next=True)
        if len(rooms) > 0:
            out += "**You are member of " + str(len(rooms)) + " group rooms**\n\n"
        else:
            out += "**No rooms found**"
        spark.postBotMessage(
            email=myself.creator,
            text=out,
            markdown=True)
    elif msg_list[0] == '/checkmember' and responseRoomId == chatRoomId:
        if len(msg_list) == 1:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage: `/checkmember <email>` to check room memberships for the email",
                markdown=True)
            req.response.set_status(204)
            return True
        else:
            target = msg_list[1]
        spark.postBotMessage(
            email=myself.creator,
            text="**Room memberships for " + target + "**\n\n----\n\n",
            markdown=True)
        deferred.defer(check_member, myself.creator, target, spark)
    elif msg_list[0] == '/deletemember' and responseRoomId == chatRoomId:
        if len(msg_list) < 3:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage: `/deletemember <email> <room-id>` to delete user with <email> from a room with <room-id>.",
                markdown=True)
            req.response.set_status(204)
            return True
        target = msg_list[1]
        ids = msg_list_wcap[2].split(',')
        for i in ids:
            next_members = spark.getMemberships(id=str(i))
            members = []
            while next_members and 'items' in next_members:
                members.extend(next_members['items'])
                next_members = spark.getMemberships(get_next=True)
            found = False
            for m in members:
                found = False
                if m['personEmail'].lower() == target:
                    found = True
                    res = spark.deleteMember(id=m['id'])
                    if res != None:
                        spark.postBotMessage(
                            email=myself.creator,
                            text="Deleted " + target + " from the room " + i,
                            markdown=True)
                    else:
                        spark.postBotMessage(
                            email=myself.creator,
                            text="Delete failed from the room " + i,
                            markdown=True)
                    break
            if not found:
                spark.postBotMessage(
                    email=myself.creator,
                    text=target + " was not found in room " + i,
                    markdown=True)
    elif msg_list[0] == '/addmember' and responseRoomId == chatRoomId:
        if len(msg_list) < 3:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage: `/addmember <email> <room-id>` to add user with <email> to a room with <room-id>.",
                markdown=True)
            req.response.set_status(204)
            return True
        ids = msg_list_wcap[2].split(',')
        logging.debug(str(msg_list_wcap))
        for i in ids:
            res = spark.addMember(id=i, email=msg_list[1])
            if res != None:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Added " + msg_list[1] + " to the room " + i,
                    markdown=True)
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text="Failed adding " + msg_list[1] + " to room " + i,
                    markdown=True)
    elif msg_list[0] == '/get' and responseRoomId == chatRoomId:
        if len(msg_list) == 2 and msg_list[1] == 'all':
            trackers = spark.loadTrackers()
            nicknames = []
            for tracker in trackers:
                nicknames.append(tracker.nickname)
        else:
            nicknames = [msg_list[1]]
        for nick in nicknames:
            msgs = spark.loadMessages(nickname=nick)
            if not msgs:
                spark.postBotMessage(
                    email=myself.creator,
                    text='**No messages from ' +
                    nick + '**', markdown=True)
            else:
                spark.postBotMessage(
                    email=myself.creator,
                    text='-------- -------- --------- --------- ---------')
                spark.postBotMessage(
                    email=myself.creator,
                    text='**Messages from: ' +
                    nick + '**', markdown=True)
                for msg in msgs:
                    msgContent = spark.getMessage(msg.id)
                    if not msgContent:
                        continue
                    text = msgContent['text']
                    room = spark.getRoom(msg.roomId)
                    spark.postBotMessage(
                        email=myself.creator,
                        text=msg.date.strftime('%c') + ' - (' + room['title'] + ')' + '\r\n' + text)
                    spark.clearMessages(nickname=nick)
    elif msg_list[0] == '/listmembers' and responseRoomId != chatRoomId:
        spark.deleteMessage(data['id'])
        if len(msg_list) == 2 and msg_list[1] == 'csv':
            csv = True
        else:
            csv = False
        members = spark.getMemberships(id=responseRoomId)
        if 'items' not in members:
            logging.info("Not able to retrieve members for room in /listmembers")
            spark.postMessage(
                id=responseRoomId,
                text="Net able to retrieve members in room to list members.")
            req.response.set_status(204)
            return True
        memberlist = ""
        sep = ""
        for m in members['items']:
            if csv:
                memberlist = memberlist + sep + m['personEmail']
                sep = ","
            else:
                memberlist = memberlist + "\n\n" + m['personDisplayName'] + " (" + m['personEmail'] + ")"
        room = spark.getRoom(id=responseRoomId)
        if 'title' in room:
            memberlist = "**Members in room: " + room['title'] + "**\n\n----\n\n" + memberlist
        spark.postBotMessage(
                email=myself.creator,
                text=memberlist, markdown=True)
    elif msg_list[0] == '/delete' and responseRoomId == chatRoomId:
        if len(msg_list) == 2 and msg_list[1] == 'deletenow':
            on_aw_delete.on_aw_delete_actor(myself=myself, req=req, auth=auth)
            myself.delete()
        else:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage: `/delete DELETENOW`", markdown=True)
    elif msg_list[0] == '/pins' and responseRoomId == chatRoomId:
        msgs = spark.getPinnedMessages()
        if msgs:
            spark.postBotMessage(
                email=myself.creator,
                text="**Your Pinned Reminders (all times are in UTC)**\n\n----\n\n",
                markdown=True)
        else:
            spark.postBotMessage(
                email=myself.creator,
                text="**You have no Pinned Reminders**",
                markdown=True)
        for m in msgs:
            if len(m.id) == 0:
                spark.postBotMessage(
                    email=myself.creator,
                    text="**" + m.timestamp.strftime('%Y-%m-%d %H:%M') + "** -- " + m.comment + "\n\n----\n\n",
                    markdown=True)
                continue
            pin = spark.getMessage(id=m.id)
            if not pin:
                logging.warn('Not able to retrieve message data for pinned message ')
                spark.postBotMessage(
                    email=myself.creator,
                    text="Not possible to retrieve pinned message details."
                )
                continue
            person = spark.getPerson(id=pin['personId'])
            room = spark.getRoom(id=pin['roomId'])
            if not person or not room:
                logging.warn('Not able to retrieve person and room data for pinned message')
                spark.postBotMessage(
                    email=myself.creator,
                    text="Not possible to retrieve pinned message person and room details."
                )
                continue
            spark.postBotMessage(
                email=myself.creator,
                text="**" + m.timestamp.strftime('%Y-%m-%d %H:%M') + "** -- " + m.comment + "\n\nFrom " +
                person['displayName'] + " (" + person['emails'][0] + ")" + " in room (" + room['title'] + ")\n\n" +
                pin['text'] + "\n\n----\n\n",
                markdown=True)
    elif msg_list[0] == '/team' and responseRoomId != chatRoomId:
        spark.deleteMessage(data['id'])
        if len(msg_list) != 3:
            spark.postBotMessage(
                email=myself.creator,
                text="Usage: `/team init|add|remove|verify|sync team_name`", markdown=True)
            req.response.set_status(204)
            return True
        team_cmd = msg_list[1]
        team_name = msg_list[2]
        team_str = myself.getProperty('team-' + team_name).value
        if not team_str:
            team_list = []
        else:
            try:
                team_list = json.loads(team_str)
            except:
                team_list = []
        members = spark.getMemberships(id=responseRoomId)
        roomData = spark.getRoom(id=responseRoomId)
        if roomData and 'title' in roomData:
            title = roomData['title']
        else:
            title = 'Unknown'
        if 'items' not in members:
            logging.info("Not able to retrieve members for room in /team")
            spark.postBotMessage(
                email=myself.creator,
                text="Not able to get members of room.")
            req.response.set_status(204)
            return True
        out = ''
        if team_cmd == 'init':
            team_list = []
            out = "**Initializing team " + team_name + " with members from room " + title + "**\n\n"
            for m in members['items']:
                out += "Added " + m['personEmail'] + "\n\n"
                team_list.append(str(m['personEmail']))
            if len(team_list) > 0:
                myself.setProperty('team-' + team_name, json.dumps(team_list))
        elif team_cmd == 'add' or team_cmd == 'remove' or team_cmd == 'verify' or team_cmd == 'sync':
            if len(team_list) == 0:
                spark.postBotMessage(
                    email=myself.creator,
                    text="You tried to use /team with a non-existent team.")
            else:
                if team_cmd == 'add':
                    out = "**Adding "
                elif team_cmd == 'remove':
                    out = "**Removing "
                elif team_cmd == 'sync':
                    out = "**Synchronizing "
                else:
                    out = "**Verifying "
                out += "team members from " + team_name + " in room " + title + "**\n\n"
                for m in members['items']:
                    try:
                        team_list.remove(m['personEmail'])
                        if team_cmd == 'remove':
                            spark.deleteMember(id=m['id'])
                            out += "Removed from room: " + m['personEmail'] + "\n\n"
                    except:
                        if team_cmd == 'verify':
                            out += "In room, but not in team: " + m['personEmail'] + "\n\n"
                        elif team_cmd == 'sync':
                            out += "Removed from room: " + m['personEmail'] + "\n\n"
                            spark.deleteMember(id=m['id'])
                for e in team_list:
                    if team_cmd == 'add' or team_cmd == 'sync':
                        spark.addMember(id=responseRoomId, email=e)
                        out += "Added to room " + e + "\n\n"
                    elif team_cmd == 'verify':
                        out += "Not in room, but in team: " + e + "\n\n"
        spark.postBotMessage(
            email=myself.creator,
            text=out,
            markdown=True)
    elif msg_list[0] == '/copyroom' and responseRoomId != chatRoomId:
        # Only allow copyroom in group rooms
        if data['roomType'] == 'direct':
            req.response.set_status(204)
            return True
        if len(msg_list) == 1:
            spark.postMessage(
                id=responseRoomId,
                text="Usage: `/copyroom New Room Title`", markdown=True)
            req.response.set_status(204)
            return True
        title = msg['text'][len(msg_list[0])+1:]
        roomData = spark.getRoom(id=responseRoomId)
        if roomData and 'teamId' in roomData:
            teamId = roomData['teamId']
        else:
            teamId = None
        room = spark.createRoom(title, teamId)
        if not room:
            spark.postMessage(
                id=responseRoomId,
                text="Not able to create new room.")
            req.response.set_status(204)
            return True
        members = spark.getMemberships(id=responseRoomId)
        if 'items' not in members:
            logging.info("Not able to retrieve members for room in /copyroom")
            spark.postMessage(
                id=responseRoomId,
                text="Created room, but not able to add members.")
            req.response.set_status(204)
            return True
        for m in members['items']:
            spark.addMember(id=room['id'], personId=m['personId'])
        spark.postMessage(
            id=responseRoomId,
            text="Created new room and added the same members as in this room.")
    elif msg_list[0] == '/box' and responseRoomId == chatRoomId:
        box = myself.getPeerTrustee(shorttype='boxbasic')
        if not box:
            spark.postBotMessage(
                email=myself.creator,
                text="Failed to create new box service.")
            req.response.set_status(204)
            return True
        if len(msg_list) > 1:
            boxRootId = myself.getProperty('boxRootId').value
            if boxRootId:
                spark.postBotMessage(
                    email=myself.creator,
                    text="You have created the Box root folder in Box and started to use it. "\
                    "You must do /nobox before you can change root folder.")
                req.response.set_status(204)
                return True
            boxRoot = msg_list_wcap[1]
        else:
            boxRoot = myself.getProperty('boxRoot').value
            if not boxRoot:
                boxRoot = 'SparkRoomFolders'
        myself.setProperty('boxRoot', boxRoot)
        spark.postBotMessage(
            email=myself.creator,
            text="Your box service is available and can be authorized at " + box['baseuri'] +
            "/www\n\n" +
            "Then use /boxfolder in group rooms to create new Box folders (created below the " +
            boxRoot + " folder).")
    elif msg_list[0] == '/boxfolder' and responseRoomId != chatRoomId:
        # boxRoot is set when issueing the /box command
        boxRoot = myself.getProperty('boxRoot').value
        if not boxRoot or len(boxRoot) == 0:
            spark.postMessage(
                id=responseRoomId,
                text="You have not authorized the Box service. Go to the 1:1 bot room and do the /box command first.")
            req.response.set_status(204)
            return True
        box = myself.getPeerTrustee(shorttype='boxbasic')
        proxy = aw_proxy.aw_proxy(peer_target=box)
        # boxRootId is set the first time a /boxfolder command is run
        boxRootId = myself.getProperty('boxRootId').value
        if not boxRootId:
            # Create the root folder
            params = {
                'name': boxRoot,
            }
            rootFolder = proxy.createResource(
                path='/resources/folders',
                params=params)
            if rootFolder and 'id' in rootFolder:
                boxRootId = rootFolder['id']
                myself.setProperty('boxRootId', boxRootId)
            else:
                if 'error' in rootFolder and rootFolder['error']['code'] == 401:
                    spark.postMessage(
                        id=responseRoomId,
                        text="You need to authorize the Box service first. Do /box from the 1:1 bot room.")
                elif 'error' in rootFolder and rootFolder['error']['code'] == 409:
                    spark.postMessage(
                        id=responseRoomId,
                        text="The folder already exists in Box. Choose a different name (/boxfolder anothername)")
                elif 'error' in rootFolder and rootFolder['error']['code'] != 401:
                    spark.postMessage(
                        id=responseRoomId,
                        text="Failed to create the Box root folder (" + rootFolder['error']['message'] + ")")
                else:
                    spark.postMessage(
                        id=responseRoomId,
                        text="Unknown error trying to create Box root folder.")
                req.response.set_status(204)
                return True
        room = spark.loadRoom(responseRoomId)
        if room and len(room.boxFolderId) > 0:
            folder = proxy.getResource('resources/folders/' + room.boxFolderId)
            if folder and 'url' in folder:
                spark.postMessage(
                    id=responseRoomId,
                    text='The box folder name for this room is **' +
                    folder['name'] + '**, and can be found at: ' +
                    folder['url'], markdown=True)
            else:
                spark.postMessage(
                    id=responseRoomId,
                    text="Unable to retrieve shared link from Box for this room's folder")
            req.response.set_status(204)
            return True
        # /boxfolder <rootfoldername>
        if len(msg_list) > 1:
            folderName = msg_list_wcap[1]
        else:
            room = spark.getRoom(responseRoomId)
            folderName = room['title']
        params = {
            'name': folderName,
            'parent': boxRootId,
            }
        emails = spark.getMemberships(id=responseRoomId)
        # Create the params['email'] list
        if emails and emails['items']:
            params['emails'] = []
            for item in emails['items']:
                if item['isMonitor'] or item['personEmail'] == myself.creator:
                    continue
                params['emails'].append(item['personEmail'])
        folder = proxy.createResource(
            path='/resources/folders',
            params=params)
        if folder and 'url' in folder:
            url = folder['url']
        else:
            url = 'No shared link available'
        if folder and 'id' in folder and 'error' not in folder:
            sub = myself.createRemoteSubscription(
                    peerid=box['peerid'],
                    target='resources',
                    subtarget='folders',
                    resource=folder['id'],
                    granularity='high')
            spark.postMessage(
                id=responseRoomId,
                text="Created a new box folder for this room with name: " + folderName +
                " and shared link: " + url + ". Also added all room members as editors.")
            spark.add2Room(roomId=responseRoomId, boxFolderId=folder['id'])
        else:
            if folder and 'error' in folder:
                if 'url' in folder:
                    spark.postMessage(
                        id=responseRoomId,
                        text='The box folder for this room can be found at: ' + folder['url'])
                else:
                    spark.postMessage(
                        id=responseRoomId,
                        text=folder['error']['message'])
            else:
                spark.postMessage(
                    id=responseRoomId,
                    text='Failed to create new folder for unknown reason.')
    elif msg_list[0] == '/noboxfolder' and responseRoomId != chatRoomId:
        room = spark.loadRoom(responseRoomId)
        if not room:
            spark.postMessage(
                id=responseRoomId,
                text="You don't have a box folder for this room. Do /boxfolder [foldername] to"\
                " create one. \n\nDefault folder name is the room name.")
        else:
            box = myself.getPeerTrustee(shorttype='boxbasic')
            proxy = aw_proxy.aw_proxy(peer_target=box)
            if not proxy.deleteResource('resources/folders/' + room.boxFolderId):
                spark.postMessage(
                    id=responseRoomId,
                    text="Failed to disconnect the Box folder from this room.")
            else:
                spark.deleteFromRoom(responseRoomId, boxfolder=True)
                spark.postMessage(
                    id=responseRoomId,
                    text="Disconnected the Box folder from this room. The Box folder was not deleted.")
    elif msg_list[0] == '/nobox' and responseRoomId == chatRoomId:
        if not myself.deletePeerTrustee(shorttype='boxbasic'):
            spark.postBotMessage(
                email=myself.creator,
                text="Failed to delete box service.")
        else:
            myself.deleteProperty('boxRoot')
            myself.deleteProperty('boxRootId')
            boxRooms = spark.loadRooms()
            for b in boxRooms:
                spark.deleteFromRoom(b.id, boxfolder=True)
            spark.postBotMessage(
                email=myself.creator,
                text="Deleted your box service.")
    req.response.set_status(204)
    return True


def on_post_subscriptions(myself, req, auth, sub, peerid, data):
    """Customizible function to process incoming callbacks/subscriptions/ callback with json body,
        return True if processed, False if not."""
    logging.debug("Got callback and processed " + sub["subscriptionid"] +
                  " subscription from peer " + peerid + " with json blob: " + json.dumps(data))
    spark = ciscospark.ciscospark(auth, myself.id)
    if 'target' in data and data['target'] == 'properties':
        if 'subtarget' in data and data['subtarget'] == 'topofmind' and 'data' in data:
            topofmind = data['data']
            toplist = topofmind['list']
            if len(toplist) == 0:
                spark.postBotMessage(
                    email=myself.creator,
                    text=topofmind['displayName'] + " (" + topofmind['email'] + ") just cleared " +
                    topofmind['title'], markdown=True)
                return True
            out = topofmind['displayName'] + " (" + topofmind['email'] + ") just updated " + topofmind['title'] + "\n\n----\n\n"
            for i, el in sorted(toplist.items()):
                out = out + "**" + i + "**: " + el + "\n\n"
            spark.postBotMessage(email=myself.creator, text=out, markdown=True)
        return True
    if 'resource' in data:
        folder_id = data['resource']
        room = spark.loadRoomByBoxFolderId(folder_id=folder_id)
        if room and 'data' in data and 'suggested_txt' in data['data']:
            spark.postMessage(room.id, '**From Box:** ' + data['data']['suggested_txt'], markdown=True)
        else:
            logging.warn('Was not able to post callback message to Spark room.')
    else:
        logging.debug('No resource in received subscription data.')
    return True
