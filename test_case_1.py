###########################################################
#
# matrixchatuser.py - The MatrixChatUser class
# -- Acts like a Matrix chat user
#
# Created: 2022-08-05
# Author: Charles V Wright <cvwright@futo.org>
# Copyright: 2022 FUTO Holdings Inc
# License: Apache License version 2.0
#
# The MatrixChatUser class extends MatrixUser to add some
# basic chatroom user behaviors.

# Upon login to the homeserver, this user spawns a second
# "background" Greenlet to act as the user's client's
# background sync task.  The "background" Greenlet sleeps and
# calls /sync in an infinite loop, and it uses the responses
# to /sync to populate the user's local understanding of the
# world state.
#
# Meanwhile, the user's main "foreground" Greenlet does the
# things that a Locust User normally does, sleeping and then
# picking a random @task to execute.  The available set of
# @tasks includes: accepting invites to join rooms, sending
# m.text messages, sending reactions, and paginating backward
# in a room.
#
###########################################################

import csv
import os
import sys
import glob
import random
import resource

import json
import logging

import gevent
from locust import task, between, TaskSet
from locust import events
from locust.runners import MasterRunner, WorkerRunner
import mimetypes

from matrixuser import MatrixUser


# Preflight ###############################################

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    # Increase resource limits to prevent OS running out of descriptors
    resource.setrlimit(resource.RLIMIT_NOFILE, (999999, 999999))

    # Multi-worker
    if isinstance(environment.runner, WorkerRunner):
        print(f"Registered 'load_users' handler on {environment.runner.client_id}")
        environment.runner.register_message("load_users", MatrixChatUser.load_users)
    # Single-worker
    elif not isinstance(environment.runner, WorkerRunner) and not isinstance(environment.runner, MasterRunner):
      # Open our list of users
      MatrixChatUser.worker_users = csv.DictReader(open("users.csv"))

# # Load our images and thumbnails
# images_folder = "images"
# image_files = glob.glob(os.path.join(images_folder, "*.jpg"))
# images_with_thumbnails = []
# for image_filename in image_files:
#   image_basename = os.path.basename(image_filename)
#   thumbnail_filename = os.path.join(images_folder, "thumbnails", image_basename)
#   if os.path.exists(thumbnail_filename):
#     images_with_thumbnails.append(image_filename)

# # Find our user avatar images
# avatars = []
# avatars_folder = "avatars"
# avatar_files = glob.glob(os.path.join(avatars_folder, "*.png"))
# Find our user avatar images
avatars = []
avatars_folder = "avatars"
avatar_files = glob.glob(os.path.join(avatars_folder, "*.png"))

video_folder = "videos"
video_files = glob.glob(os.path.join(video_folder, "*.mp4"))

# Pre-generate some messages for the users to send
lorem_ipsum_text = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sed est facilisis, tristique quam sit amet, bibendum sapien. In tincidunt consectetur mi in condimentum. Donec varius vel diam cursus egestas. Donec mollis a mauris euismod pretium. Etiam in sollicitudin odio, ac interdum dolor. Interdum et malesuada fames ac ante ipsum primis in faucibus. Aliquam cursus porttitor nibh sit amet semper. Donec dictum, ex finibus ornare fringilla, dui purus feugiat metus, ornare lacinia dui nibh et nisi. Nam a mollis neque. Sed mollis quam ac nisl feugiat malesuada. Aliquam id posuere arcu, ac venenatis ex. Aliquam venenatis erat et bibendum ornare. Aenean in sollicitudin urna. Duis gravida elit eros, hendrerit aliquet massa volutpat vel. Nulla facilisi. Aenean interdum est quis magna dignissim tincidunt. Curabitur odio nisi, maximus id tempus a, varius et enim. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec in ex nec sapien ultricies tempor non eget dui. Maecenas egestas orci vitae augue cursus rhoncus. Nam dignissim leo ac odio tristique dignissim.
"""
lorem_ipsum_words = lorem_ipsum_text.split()

lorem_ipsum_messages = {}
for i in range(1, len(lorem_ipsum_words)+1):
  lorem_ipsum_messages[i] = " ".join(lorem_ipsum_words[:i])

###########################################################

class MatrixChatUser(MatrixUser):
  worker_id = None
  worker_users = []

  @staticmethod
  def load_users(environment, msg, **_kwargs):
      MatrixChatUser.worker_users = iter(msg.data)
      MatrixChatUser.worker_id = environment.runner.client_id
      logging.info("Worker [%s] Received %s users", environment.runner.client_id, len(msg.data))

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  def on_start(self):
    try:
      user_dict = next(MatrixChatUser.worker_users)
    except StopIteration:
      gevent.sleep(999999)
      return

    self.login_from_csv(user_dict)

    if not (self.user_id is None) and not (self.access_token is None):
      self.start_syncing()

    if self.username is None or self.password is None:
      logging.error("No username or password")
      self.environment.runner.quit()
    else:
      while self.user_id is None or self.access_token is None:
        self.login(start_syncing = True, log_request = True)

  def on_stop(self):
    pass

  @task
  def send_text(self):
    room_id = self.get_random_roomid()
    if room_id is None:
      return

    self.set_typing(room_id, True)
    # delay = random.expovariate(1.0 / 5.0)
    # gevent.sleep(delay)

    message_len = round(random.lognormvariate(1.0, 1.0))
    message_len = min(message_len, len(lorem_ipsum_words))
    message_len = max(message_len, 1)
    message_text = lorem_ipsum_messages[message_len]

    event = {
      "type": "m.room.message",
      "content": {
        "msgtype": "m.text",
        "body": message_text,
      }
    }
    with self.send_matrix_event(room_id, event) as response:
      if "error" in response.js:
        logging.error("User [%s] failed to send m.text to room [%s]" % (self.username, room_id))

  # @task
  # def send_image(self):
  #   room_id = self.get_random_roomid()
  #   if room_id is None:
  #     return

  #   # Escolha um arquivo de avatar para enviar
  #   image_path = random.choice(avatar_files)
  #   self.set_typing(room_id, True)
    
  #   # Guess the mimetype of the file
  #   (mime_type, encoding) = mimetypes.guess_type(image_path)
  #   if mime_type is None:
  #     logging.error("User [%s] Failed to determine MIME type for file %s" % (self.username, image_path))
  #     return

  #   # Read the contents of the file
  #   with open(image_path, 'rb') as f:
  #     data = f.read()
      
  #   # Upload the file to Matrix
  #   mxc_url = self.upload_matrix_media(data, mime_type)
  #   if mxc_url is None:
  #     logging.error("User [%s] Failed to upload image %s" % (self.username, image_path))
  #     return
  #   # url = "/_matrix/client/%s/profile/%s/avatar_url" % (self.matrix_version, self.user_id)
  #   # body = {
  #   #   "avatar_url": mxc_url
  #   # }
    
  #   # Create the message event
  #   event = {
  #     "type": "m.room.message",
  #     "content": {
  #       "msgtype": "m.image",
  #       "body": os.path.basename(image_path),
  #       "url": mxc_url,
  #       "info": {
  #         "mimetype": mime_type,
  #         "size": len(data),
  #         # Adicione outras informações da imagem conforme necessário
  #       }
  #     }
  #   }
    
  #   # Send the image message to the room
  #   with self.send_matrix_event(room_id, event) as response:
  #     if "error" in response.js:
  #       logging.error("User [%s] failed to send image to room [%s]" % (self.username, room_id))
  #     else:
  #       logging.info("User [%s] successfully sent image to room [%s]" % (self.username, room_id))
  
  # @task
  # def send_video(self):
  #   room_id = self.get_random_roomid()
  #   if room_id is None:
  #     return

  #   # Escolha um arquivo de avatar para enviar
  #   video_path = random.choice(video_files)
  #   self.set_typing(room_id, True)
    
  #   # Guess the mimetype of the file
  #   (mime_type, encoding) = mimetypes.guess_type(video_path)
  #   if mime_type is None:
  #     logging.error("User [%s] Failed to determine MIME type for file %s" % (self.username, video_path))
  #     return

  #   # Read the contents of the file
  #   with open(video_path, 'rb') as f:
  #     data = f.read()
      
  #   # Upload the file to Matrix
  #   mxc_url = self.upload_matrix_media(data, mime_type)
  #   if mxc_url is None:
  #     logging.error("User [%s] Failed to upload video %s" % (self.username, video_path))
  #     return
  #   # url = "/_matrix/client/%s/profile/%s/avatar_url" % (self.matrix_version, self.user_id)
  #   # body = {
  #   #   "avatar_url": mxc_url
  #   # }
    
  #   # Create the message event
  #   event = {
  #     "type": "m.room.message",
  #     "content": {
  #       "msgtype": "m.video",
  #       "body": os.path.basename(video_path),
  #       "url": mxc_url,
  #       "info": {
  #         "mimetype": mime_type,
  #         "size": len(data),
  #         # Adicione outras informações da imagem conforme necessário
  #       }
  #     }
  #   }
    
  #   # Send the image message to the room
  #   with self.send_matrix_event(room_id, event) as response:
  #     if "error" in response.js:
  #       logging.error("User [%s] failed to send video to room [%s]" % (self.username, room_id))
  #     else:
  #       logging.info("User [%s] successfully sent video to room [%s]" % (self.username, room_id))
  # Comentando outras tarefas para focar apenas no envio de mensagens de texto
  # @task(1)
  # def do_nothing(self):
  #   self.wait()

  # @task(4)
  # def look_at_room(self):
  #   room_id = self.get_random_roomid()
  #   if room_id is None:
  #     return
  #   self.load_data_for_room(room_id)

  #   messages = self.recent_messages.get(room_id, [])
  #   if messages is None or len(messages) < 1:
  #     return

  #   last_msg = messages[-1]
  #   event_id = last_msg.get("event_id", None)
  #   if event_id is not None:
  #     self.send_read_receipt(room_id, event_id)

  # @task
  # def paginate_room(self):
  #   room_id = self.get_random_roomid()
  #   token = self.earliest_sync_tokens.get(room_id, self.initial_sync_token)
  #   if room_id is None or token is None:
  #     return
  #   url = "/_matrix/client/%s/rooms/%s/messages?dir=b&from=%s" % (self.matrix_version, room_id, token)
  #   label = "/_matrix/client/%s/rooms/_/messages" % self.matrix_version
  #   with self._matrix_api_call("GET", url, name=label) as response:
  #     if not "chunk" in response.js:
  #       logging.warning("User [%s] GET /messages failed for room %s" % (self.username, room_id))
  #     if "end" in response.js:
  #       self.earliest_sync_tokens[room_id] = response.js["end"]

  # @task(1)
  # def go_afk(self):
  #   logging.info("User [%s] going away from keyboard" % self.username)
  #   away_time = random.expovariate(1.0 / 600.0)
  #   gevent.sleep(away_time)

  # @task(1)
  # def change_displayname(self):
  #   user_number = self.username.split(".")[-1]
  #   random_number = random.randint(1,1000)
  #   new_name = "User %s (random=%d)" % (user_number, random_number)
  #   self.set_displayname(displayname=new_name)

  # @task(3)
  # class ChatInARoom(TaskSet):

  #   def wait_time(self):
  #     expected_wait = 25.0
  #     rate = 1.0 / expected_wait
  #     return random.expovariate(rate)

  #   def on_start(self):
  #     if len(self.user.joined_room_ids) == 0:
  #       self.interrupt()
  #     else:
  #       self.room_id = self.user.get_random_roomid()
  #       if self.room_id is None:
  #         self.accept_invites()
  #         self.interrupt()
  #       else:
  #         self.user.load_data_for_room(self.room_id)

  #   @task
  #   def send_text(self):

  #     self.user.set_typing(self.room_id, True)
  #     delay = random.expovariate(1.0 / 5.0)
  #     gevent.sleep(delay)

  #     message_len = round(random.lognormvariate(1.0, 1.0))
  #     message_len = min(message_len, len(lorem_ipsum_words))
  #     message_len = max(message_len, 1)
  #     message_text = lorem_ipsum_messages[message_len]

  #     event = {
  #       "type": "m.room.message",
  #       "content": {
  #         "msgtype": "m.text",
  #         "body": message_text,
  #       }
  #     }
  #     with self.user.send_matrix_event(self.room_id, event) as response:
  #       if not "event_id" in response.js:
  #         logging.warning("User [%s] Failed to send/chat in room %s" % (self.user.username, self.room_id))

  #   @task
  #   def send_image(self):
  #     pass

  #   @task
  #   def send_reaction(self):
  #     messages = self.user.recent_messages.get(self.room_id, [])
  #     if messages is None or len(messages) < 1:
  #       return
  #     message = random.choice(messages)
  #     reaction = random.choice(["💩","👍","❤️", "👎", "🤯", "😱", "👏"])
  #     event = {
  #       "type": "m.reaction",
  #       "content": {
  #         "m.relates_to": {
  #           "rel_type": "m.annotation",
  #           "event_id": message["event_id"],
  #           "key": reaction,
  #         }
  #       }
  #     }
  #     with self.user.send_matrix_event(self.room_id, event) as _response:
  #       pass

  #   @task
  #   def stop(self):
  #     self.interrupt()

  #   tasks = {
  #     send_text: max(1, round(random.gauss(15,4))),
  #     send_image: random.choice([0,0,0,1,1,2]),
  #     send_reaction: random.choice([0,0,1,1,1,2,3]),
  #     stop: 1,
  #   }
