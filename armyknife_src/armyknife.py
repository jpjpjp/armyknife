import uuid
import time
import datetime
# noinspection PyPackageRequirements
import pytz
from actingweb import attribute


class ArmyKnife:

    def __init__(self, actor_id=None, config=None):
        self.autoReminderPrefix = "#/"
        self.actor_id = actor_id
        self.config = config

    def load_room(self, spark_id):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        room = bucket.get_attr(name=spark_id)
        if room and 'data' in room:
            return room["data"]
        return None

    def load_rooms(self):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        return bucket.get_bucket()

    def add_uuid_to_room(self, room_id):
        room = self.load_room(room_id)
        if room and 'uuid' in room:
            return room["uuid"]
        room_uuid = uuid.uuid5(uuid.NAMESPACE_URL, str(room_id)).hex
        newroom = self.add_to_room(room_id=room_id, room_uuid=room_uuid)
        return newroom["uuid"]

    def add_to_room(self, room_id=None, room_uuid='', box_folder_id=''):
        """ Adds properties to a room

            Remember to update delete_from_room() deletion if new attributes are added.
        """
        if not room_id:
            return None
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        room = bucket.get_attr(name=room_id)
        if not room:
            room = {}
        if room_uuid:
            room["uuid"] = room_uuid
        if box_folder_id:
            room["boxFolderId"] = box_folder_id
        bucket.set_attr(name=room_id, data=room)
        return room

    def delete_from_room(self, room_id=None, del_uuid=False, del_boxfolder=False):
        if not room_id:
            return False
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        room = bucket.get_attr(room_id).get("data", None)
        if not room:
            return False
        if del_uuid:
            del room["uuid"]
        if del_boxfolder:
            del room["boxFolderId"]
        # Delete entire room if all attributes have been cleared
        # Update here if new attributes are added
        if len(room) == 0:
            bucket.delete_attr(room_id)
        else:
            bucket.set_attr(room_id, data=room)
        return True

    def delete_rooms(self):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        bucket.delete_bucket()
        return True

    def delete_room(self, room_id):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        return bucket.delete_attr(room_id)

    def load_room_by_uuid(self, room_id):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        rooms = bucket.get_bucket()
        for k, v in rooms.items():
            if v["data"]["uuid"] == room_id:
                ret = {
                    'id': k,
                    'uuid': v["data"]["uuid"],
                }
                if 'boxFolderId' in v["data"]:
                    ret['boxFolderId'] = v["data"]["boxfolderId"]
                return ret
        return None

    def load_room_by_boxfolder_id(self, folder_id):
        bucket = attribute.Attributes(actor_id=self.actor_id, bucket="rooms", config=self.config)
        rooms = bucket.get_bucket()
        for k, v in rooms:
            if v["data"]["boxFolderId"] == folder_id:
                return {
                    'id': k,
                    'uuid': v["data"]["uuid"],
                    'boxFolderId': v["data"]["boxfolderId"],
                }
        return None

    def process_message(self, msg=None, save=True):
        if not msg:
            return False
        # Is this message from a registered person to track?
        person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
        person = person_bucket.get_attr(msg['personEmail'])
        if not person:
            return False
        if not save:
            return True
        message_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="messages", config=self.config)
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

    def load_messages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
            persons = person_bucket.get_bucket()
            for k, v in persons.items():
                if v["data"]["nickname"] == nickname:
                    email = k
        if not email:
            return False
        message_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="messages", config=self.config)
        msgs = message_bucket.get_bucket()
        ret = []
        for l, v in msgs.items():
            if v['data']['personEmail'] == email:
                ret.append({
                    "timestamp": v["timestamp"],
                    "id": l,
                    "roomId": v["data"]["roomId"],
                    "personId": v["data"]["personId"],
                    "personEmail": v["data"]["personEmail"],
                })
        ret2 = sorted(ret, key=lambda d: d['timestamp'])
        return ret2

    def clear_messages(self, email=None, nickname=None):
        if not email and not nickname:
            return False
        if not email:
            person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
            persons = person_bucket.get_bucket()
            for k, v in persons.items():
                if v["data"]["nickname"] == nickname:
                    email = k
        message_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="messages", config=self.config)
        msgs = message_bucket.get_bucket()
        for l, v in msgs.items():
            if v["data"]["personEmail"] == email:
                message_bucket.delete_attr(l)

    def add_tracker(self, email, nickname, display_name=None, avatar=''):
        if not email or not nickname:
            return False
        person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
        person = person_bucket.get_attr(email)
        if person:
            return False
        if not display_name:
            display_name = nickname
        person_bucket.set_attr(
            email,
            data={
                "nickname": nickname,
                "displayName": display_name,
                "avatar": avatar
            })
        return True

    def delete_tracker(self, email):
        person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
        if person_bucket.delete_attr(email):
            self.clear_messages(email=email)
            return True
        return False

    def load_trackers(self):
        person_bucket = attribute.Attributes(actor_id=self.actor_id, bucket="persons", config=self.config)
        trackers = person_bucket.get_bucket()
        ret = []
        if not trackers:
            return ret
        for p, v in trackers.items():
            ret.append({
                "email": p,
                "nickname": v["data"]["nickname"],
                "displayName": v["data"]["displayName"],
                "avatar": v["data"]["avatar"],
            }
            )
        return ret

    def save_pinned_message(self, msg_id=None, comment=None, timestamp=None):
        if not timestamp:
            return False
        if not msg_id:
            msg_id = ''
        ts = str(time.time())
        if not comment:
            comment = ''
        message_bucket = attribute.Attributes("pinned", self.actor_id, config=self.config)
        message_bucket.set_attr(
            ts,
            data={
                "actor_id": self.actor_id,
                "id": msg_id,
                "comment": comment
            },
            timestamp=timestamp
        )
        return True

    def get_pinned_messages(self):
        message_bucket = attribute.Attributes("pinned", self.actor_id, config=self.config)
        res = message_bucket.get_bucket()
        # Remove autoreminder messages
        msgs = {}
        for m, v in res.items():
            if v["data"]["comment"][0:2] != self.autoReminderPrefix:
                msgs[m] = v
        ret = []
        for m, v in msgs.items():
            ret.append({
                "id": v["data"]["id"],
                "actor_id": self.actor_id,
                "comment": v["data"]["comment"],
                "timestamp": v["timestamp"]
            })
        return ret

    def delete_pinned_messages(self, comment=None):
        message_bucket = attribute.Attributes("pinned", self.actor_id, config=self.config)
        msgs = message_bucket.get_bucket()
        for m, v in msgs.items():
            # If comment is specified, only delete that message
            if comment and comment != v["data"]["comment"]:
                continue
            # If comment is not specified, do not delete special auto reminders
            if not comment and v["data"]["comment"][0:2] == self.autoReminderPrefix:
                continue
            message_bucket.delete_attr(m)

    def get_due_pinned_messages(self):
        # Here keep auto-reminders
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.utc)
        message_bucket = attribute.Buckets("pinned", config=self.config)
        msgs = message_bucket.fetch()
        ret = []
        if not msgs:
            return ret
        for m, v in msgs.items():
            for a, b in v.items():
                if b["timestamp"] <= now:
                    ret.append({
                        "actor_id": m,
                        "id": b["data"]["id"],
                        "comment": b["data"]["comment"],
                        "timestamp": b["timestamp"]
                    })
                    del_msg = attribute.Attributes("pinned", m, config=self.config)
                    del_msg.delete_attr(a)
        return ret

    def save_perm_attribute(self, name=None, value=None):
        if not name:
            return False
        if not value:
            value = ''
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.utc)
        bucket = attribute.Attributes("perm", self.actor_id, config=self.config)
        bucket.set_attr(
            name,
            data=value,
            timestamp=now
        )
        return True

    def get_perm_attribute(self, name=None):
        if not name:
            return None
        perm_bucket = attribute.Attributes('perm', self.actor_id, config=self.config)
        return perm_bucket.get_attr(name)

    def get_perm_attributes(self):
        perm_attrs = attribute.Attributes('perm', self.actor_id, config=self.config)
        attrs = perm_attrs.get_bucket()
        ret = {}
        if not attrs:
            return ret
        for p, v in attrs.items():
            ret[p] = {
                'data': v['data'],
                'timestamp': v['timestamp']
            }
        return ret

    def stats_incr_command(self, command=None):
        if not command:
            return False
        message_bucket = attribute.Attributes("stats", "commands", config=self.config)
        attrs = message_bucket.get_attr(command)
        if attrs:
            count = attrs["data"]["count"]
            count += 1
        else:
            count = 1
        message_bucket.set_attr(
            command,
            data={
                "command": command,
                "count": count
            }
        )
        return True

    def get_stats_commands(self):
        stat_bucket = attribute.Attributes("stats", "command", config=self.config)
        stats = stat_bucket.get_bucket()
        ret = []
        if not stats:
            return ret
        for p, v in stats.items():
            ret.append({
                "command": v["data"]["command"],
                "count": v["data"]["count"]
            }
            )
        return ret
