#!/usr/bin/env python
#
import cgi
import wsgiref.handlers
from actingweb import actor
from actingweb import oauth
from actingweb import config
from spark import ciscospark

import webapp2

__all__ = [
    'on_aw_delete_actor',
]


def on_aw_delete_actor(myself, req, auth):
    spark = ciscospark.ciscospark(auth, myself.id)
    spark.clearMessages(email=myself.creator)
    trackers = spark.loadTrackers()
    for tracker in trackers:
        spark.deleteTracker(tracker.email)
    chatRoom = myself.getProperty('chatRoomId')
    if chatRoom and chatRoom.value:
        spark.postMessage(
            chatRoom.value, "**Deleting all your data and account.**\n\nThe 1:1 room with the bot will remain."\
            " Type /init there if you want to create a new account.",
            markdown=True)
        spark.deleteRoom(chatRoom.value)
    firehoseId = myself.getProperty('firehoseId')
    if firehoseId and firehoseId.value:
        spark.unregisterWebHook(firehoseId.value)
    spark.deleteRooms()
    spark.deletePinnedMessages()
    spark.deletePinnedMessages(comment="#/TOPOFMIND")
    if '@actingweb.net' not in myself.creator and myself.creator != "creator" and myself.creator != "trustee":
        spark.postAdminMessage(text='User just left: ' + myself.creator)
    return
