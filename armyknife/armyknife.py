import uuid
import time
import datetime
import pytz
from actingweb import attribute


class armyknife():

    def __init__(self, actorId=None, config=None):
        self.autoReminderPrefix = "#/"
        self.actorId = actorId
        self.config = config

    def loadRoom(self, id):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        room = bucket.get_attr(name=id)
        if room and 'data' in room:
            return room["data"]
        return None

    def loadRooms(self):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        return bucket.get_bucket()

    def addUUID2room(self, roomId):
        room = self.loadRoom(roomId)
        if room and uuid in room:
            return room["uuid"]
        room_uuid = uuid.uuid5(uuid.NAMESPACE_URL, roomId.encode(
            encoding='ascii')).get_hex()
        newroom = self.add2Room(roomId=roomId, uuid=room_uuid)
        return newroom["uuid"]

    def add2Room(self, roomId=None, uuid='', boxFolderId=''):
        """ Adds properties to a room

            Remember to update deleteFromRoom() deletion if new attributes are added.
        """
        if not roomId:
            return None
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        room = bucket.get_attr(name=roomId)
        if not room:
            room = {}
        if uuid:
            room["uuid"] = uuid
        if boxFolderId:
            room["boxFolderId"] = boxFolderId
        bucket.set_attr(name=roomId, data=room)
        return room

    def deleteFromRoom(self, roomId=None, uuid=False, boxfolder=False):
        if not roomId:
            return False
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        room = bucket.get_attr(roomId)["data"]
        if not room:
            return False
        if uuid:
            del room["uuid"]
        if boxfolder:
            del room["boxFolderId"]
        # Delete entire room if all attributes have been cleared
        # Update here if new attributes are added
        if len(room) == 0:
            bucket.delete_attr(roomId)
        else:
            bucket.set_attr(roomId, data=room)
        return True

    def deleteRooms(self):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        bucket.delete_bucket()
        return True

    def deleteRoom(self, roomId):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        return bucket.delete_attr(roomId)

    def loadRoomByUuid(self, uuid):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        rooms = bucket.get_bucket()
        for k,v in rooms.iteritems():
            if v["data"]["uuid"] == uuid:
                ret = {
                    'id': k,
                    'uuid': v["data"]["uuid"],
                }
                if 'boxFolderId' in v["data"]:
                    ret['boxFolderId'] = v["data"]["boxfolderId"]
                return ret
        return None

    def loadRoomByBoxFolderId(self, folder_id):
        bucket = attribute.attributes(actorId=self.actorId, bucket="rooms", config=self.config)
        rooms = bucket.get_bucket()
        for k,v in rooms:
            if v["data"]["boxFolderId"] == folder_id:
                return {
                    'id': k,
                    'uuid': v["data"]["uuid"],
                    'boxFolderId': v["data"]["boxfolderId"],
                }
        return None

    def processMessage(self, msg=None):
        if not msg:
            return False
        # Is this message from a registered person to track?
        person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
        person = person_bucket.get_attr(msg['personEmail'])
        if not person:
            return False
        message_bucket = attribute.attributes(actorId=self.actorId, bucket="messages", config=self.config)
        message_bucket.set_attr(
            name=msg['id'],
            data={
            "roomId": msg['roomId'],
            "personId": msg['personId'],
            "personEmail": msg['personEmail'],
            },
            timestamp=datetime.datetime.utcnow()
        )
        return True

    def loadMessages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
            persons = person_bucket.get_bucket()
            for k,v in persons.items():
                if v["data"]["nickname"] == nickname:
                    email = k
        if not email:
            return False
        message_bucket = attribute.attributes(actorId=self.actorId, bucket="messages", config=self.config)
        msgs = message_bucket.get_bucket()
        ret = []
        for l,v in msgs.items():
            ret.append({
                "timestamp": v["timestamp"],
                "id": l,
                "roomId": v["data"]["roomId"],
                "personId": v["data"]["personId"],
                "personEmail": v["data"]["personEmail"],
            })
        ret2 = sorted(ret, key=lambda d:d['timestamp'])
        return ret2

    def clearMessages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
            persons = person_bucket.get_bucket()
            for k,v in persons.items():
                if v["data"]["nickname"] == nickname:
                    email = k
        message_bucket = attribute.attributes(actorId=self.actorId, bucket="messages", config=self.config)
        msgs=message_bucket.get_bucket()
        for l, v in msgs.items():
            if v["data"]["personEmail"] == email:
                message_bucket.delete_attr(l)

    def addTracker(self, email, nickname, displayName=None, avatar=''):
        if not email or not nickname:
            return False
        person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
        person = person_bucket.get_attr(email)
        if person:
            return False
        if not displayName:
            displayName=nickname
        person_bucket.set_attr(
            email,
            data={
                "nickname": nickname,
                "displayName": displayName,
                "avatar": avatar
            })
        return True

    def deleteTracker(self, email):
        person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
        if person_bucket.delete_attr(email):
            self.clearMessages(email=email)
            return True
        return False

    def loadTrackers(self):
        person_bucket = attribute.attributes(actorId=self.actorId, bucket="persons", config=self.config)
        trackers = person_bucket.get_bucket()
        ret = []
        for p, v in trackers.items():
            ret.append({
                "email": p,
                "nickname": v["data"]["nickname"],
                "displayName": v["data"]["displayName"],
                "avatar": v["data"]["avatar"],
            }
            )
        return ret

    def savePinnedMessage(self, id=None, comment=None, timestamp=None):
        if not timestamp:
            return False
        if not id:
            id = ''
        ts = str(time.time())
        if not comment:
            comment = ''
        message_bucket = attribute.attributes("pinned", self.actorId, config=self.config)
        message_bucket.set_attr(
            ts,
            data={
                "actorId": self.actorId,
                "id": id,
                "comment": comment
            },
            timestamp=timestamp
        )
        return True

    def getPinnedMessages(self):
        message_bucket = attribute.attributes("pinned", self.actorId, config=self.config)
        res = message_bucket.get_bucket()
        # Remove autoreminder messages
        msgs = {}
        for m, v in res.iteritems():
            if v["data"]["comment"][0:2] != self.autoReminderPrefix:
                msgs[m] = v
        ret = []
        for m, v in msgs.iteritems():
            ret.append({
                "id": v["data"]["id"],
                "actorId": self.actorId,
                "comment": v["data"]["comment"],
                "timestamp": v["timestamp"]
            })
        return ret

    def deletePinnedMessages(self, comment=None):
        message_bucket = attribute.attributes("pinned", self.actorId, config=self.config)
        msgs = message_bucket.get_bucket()
        for m, v in msgs.iteritems():
            # If comment is specified, only delete that message
            if comment and comment != v["data"]["comment"]:
                continue
            # If comment is not specified, do not delete special auto reminders
            if not comment and v["data"]["comment"][0:2] == self.autoReminderPrefix:
                continue
            message_bucket.delete_attr(m)

    def getDuePinnedMessages(self):
        # Here keep auto-reminders
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.utc)
        message_bucket = attribute.buckets("pinned", config=self.config)
        msgs = message_bucket.fetch()
        ret = []
        if not msgs:
            return ret
        for m, v in msgs.iteritems():
            for a, b in v.iteritems():
                if b["timestamp"] <= now:
                    ret.append({
                        "actorId": m,
                        "id": b["data"]["id"],
                        "comment": b["data"]["comment"],
                        "timestamp": b["timestamp"]
                    })
                    del_msg = attribute.attributes("pinned", m, config=self.config)
                    del_msg.delete_attr(a)
        return ret
