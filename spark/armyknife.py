import uuid
from google.appengine.ext import ndb
import datetime


class Room(ndb.Model):
    actorId = ndb.StringProperty(required=True)
    id = ndb.StringProperty(required=True)
    title = ndb.TextProperty()
    uuid = ndb.StringProperty()
    boxFolderId = ndb.StringProperty()


class PinnedMessage(ndb.Model):
    actorId = ndb.StringProperty(required=True)
    id = ndb.StringProperty()
    comment = ndb.TextProperty()
    timestamp = ndb.DateTimeProperty(required=True)


class Message(ndb.Model):
    actorId = ndb.StringProperty(required=True)
    id = ndb.StringProperty(required=True)
    roomId = ndb.StringProperty(required=True)
    personId = ndb.StringProperty()
    personEmail = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class Person(ndb.Model):
    actorId = ndb.StringProperty(required=True)
    id = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    displayName = ndb.StringProperty()
    nickname = ndb.StringProperty()
    avatar = ndb.StringProperty()


class armyknife():

    def addUUID2room(self, roomId):
        room = self.loadRoom(roomId)
        if room and room.uuid:
            return room.uuid
        room = self.getRoom(roomId)
        if room:
            room_uuid = uuid.uuid5(uuid.NAMESPACE_URL, roomId.encode(
                encoding='ascii')).get_hex()
            newroom = self.add2Room(roomId=roomId, uuid=room_uuid)
        return newroom.uuid

    def add2Room(self, roomId=None, uuid='', boxFolderId=''):
        """ Adds properties to a room

            Remember to update deleteFromRoom() deletion if new attributes are added.
        """
        if not roomId:
            return None
        newroom = self.loadRoom(roomId)
        if newroom:
            if uuid:
                newroom.uuid = uuid
            if boxFolderId:
                newroom.boxFolderId = boxFolderId
        else:
            room = self.getRoom(roomId)
            if room and 'id' in room:
                newroom = Room(actorId=self.actorId,
                               id=room['id'],
                               uuid=uuid,
                               boxFolderId=boxFolderId,
                               title=room['title'])
            else:
                return None
        newroom.put()
        return newroom

    def deleteFromRoom(self, roomId=None, uuid=False, boxfolder=False):
        if not roomId:
            return False
        newroom = self.loadRoom(roomId)
        if not newroom:
            return False
        if uuid:
            newroom.uuid = ''
        if boxfolder:
            newroom.boxFolderId = ''
        # Delete entire room if all attributes have been cleared
        # Update here if new attributes are added
        if len(newroom.uuid) == 0 and len(newroom.boxFolderId) == 0:
            newroom.key.delete()
        else:
            newroom.put()
        return True

    def deleteRooms(self):
        rooms = Room.query(Room.actorId == self.actorId).fetch()
        for room in rooms:
            room.key.delete()
        return True

    def deleteRoom(self, roomId):
        room = Room.query(Room.actorId == self.actorId, Room.id == roomId).get()
        if room:
            room.key.delete()
            return True
        return False

    def loadRoomByUuid(self, uuid):
        return Room.query(Room.actorId == self.actorId, Room.uuid == uuid).get()

    def loadRoomByBoxFolderId(self, folder_id):
        return Room.query(Room.actorId == self.actorId, Room.boxFolderId == folder_id).get()

    def processMessage(self, msg=None):
        if not msg:
            return False
        # Is this message from a registered person to track?
        result = Person.query(Person.actorId == self.actorId,
                              Person.email == msg['personEmail']).get()

        if result:
            message = Message(actorId=self.actorId,
                              id=msg['id'],
                              roomId=msg['roomId'],
                              personId=msg['personId'],
                              personEmail=msg['personEmail'])
            message.put()
            return True
        else:
            return False

    def loadMessages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person = Person.query(Person.actorId == self.actorId, Person.nickname == nickname).get()
            if person:
                email = person.email
        if not email:
            return False
        return Message.query(Message.actorId == self.actorId, Message.personEmail == email).order(Message.date).fetch()

    def clearMessages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person = Person.query(Person.actorId == self.actorId, Person.nickname == nickname).get()
            email = person.email
        results = Message.query(Message.actorId == self.actorId,
                                Message.personEmail == email).fetch()
        for result in results:
            result.key.delete()

    def addTracker(self, email, nickname, displayName=None, avatar=''):
        if not email or not nickname:
            return False
        result = Person.query(Person.actorId == self.actorId, Person.email == email).get()
        if result:
            return False
        if not displayName:
            displayName=nickname
        person = Person(actorId=self.actorId,
                        id=result['id'],
                        email=email,
                        nickname=nickname,
                        displayName=displayName,
                        avatar=avatar)
        person.put()
        return True

    def deleteTracker(self, email):
        result = Person.query(Person.actorId == self.actorId, Person.email == email).get()
        if result:
            result.key.delete()
            msgs = Message.query(Message.actorId == self.actorId,
                                 Message.personEmail == email).fetch()
            if msgs:
                for msg in msgs:
                    msg.key.delete()
            return True
        return False

    def loadTrackers(self):
        return Person.query(Person.actorId == self.actorId).fetch()

    def loadRoom(self, id):
        return Room.query(Room.actorId == self.actorId, Room.id == id).get()

    def loadRooms(self):
        return Room.query(Room.actorId == self.actorId).fetch()

    def savePinnedMessage(self, id=None, comment=None, timestamp=None):
        if not timestamp:
            return False
        if not id:
            id = ''
        if not comment:
            comment = ''
        message = PinnedMessage(
            actorId=self.actorId,
            id=id,
            timestamp=timestamp,
            comment=comment)
        message.put()
        return True

    def getPinnedMessages(self):
        msgs = PinnedMessage.query(PinnedMessage.actorId == self.actorId).order(PinnedMessage.timestamp).fetch()
        # Remove autoreminder messages
        msgs = [msg for msg in msgs if msg.comment[0:2] != self.autoReminderPrefix]
        return msgs

    def deletePinnedMessages(self, comment=None):
        msgs = PinnedMessage.query(PinnedMessage.actorId == self.actorId).order(PinnedMessage.timestamp).fetch()
        for msg in msgs:
            # If comment is specified, only delete that message
            if comment and comment != msg.comment:
                continue
            # If comment is not specified, do not delete special auto reminders
            if not comment and msg.comment[0:2] == self.autoReminderPrefix:
                continue
            msg.key.delete(use_cache=False)

    def getDuePinnedMessages(self):
        # Here keep auto-reminders
        now = datetime.datetime.utcnow()
        msgs = PinnedMessage.query(PinnedMessage.timestamp <= now).fetch()
        for msg in msgs:
            msg.key.delete(use_cache=False)
        return msgs
