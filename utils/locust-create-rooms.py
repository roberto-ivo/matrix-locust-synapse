#!/bin/env python3

import csv
import os
import signal
import sys
import glob
import random

import json
import logging

from locust import task, FastHttpUser, between, constant, TaskSet
from locust import events
from locust.runners import MasterRunner, WorkerRunner

import gevent

from matrixuser import MatrixUser



# Preflight ####################################################################

user_reader = csv.DictReader(open("users.csv"))

# Load our list of rooms to be created
logging.info("Loading rooms list")
rooms = {}
with open("rooms.json", "r") as rooms_jsonfile:
  rooms = json.load(rooms_jsonfile)
logging.info("Success loading rooms list")

# Now we need to sort of invert the list
# We need a list of the rooms to be created by each user,
# with the list of other users who should be invited to each
rooms_for_users = {}
for room_name, room_users in rooms.items():
  first_user = room_users[0]
  user_rooms = rooms_for_users.get(first_user, [])
  room_info = {
    "name": room_name,
    "users": room_users[1:]
  }
  user_rooms.append(room_info)
  rooms_for_users[first_user] = user_rooms

# Quit handler to suppress uncessary stack trace printout on graceful exit
@events.quit.add_listener
def on_locust_quit(exit_code):
  if exit_code == 1:
    print("Received SIGTERM or another exception. Quitting...")
    sys.exit(0)

# Scream bloody murder if someone tries to run this distributed
@events.init.add_listener
def on_locust_init(environment, **_kwargs):
  if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, WorkerRunner):
    print("Error: This script does not support distributed load generation at this time.\nPlease run this in single-process mode without --master or --worker.")
    sys.exit(1)

###############################################################################


class MatrixRoomCreatorUser(MatrixUser):

  # Indicates the number of users who have completed their room creation task
  num_users_rooms_created = 0
  wait_time = between(1,3)

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)


  @task
  def create_rooms_for_user(self):

    # Here we override the fancy distributed load generation stuff in MatrixUser,
    # because we need to make sure that each user's rooms are created exactly once.
    # Nobody should be left out, and there's no point in attempting to create the
    # same set of rooms twice.
    try:
      user_dict = next(user_reader)
    except StopIteration:
      # We can't shut down the worker until all users are registered, so return
      # early to stop this individual co-routine
      gevent.sleep(999999)
      return

    self.username = user_dict["username"]
    self.password = user_dict["password"]

    if self.username is None or self.password is None:
      #print("Error: Couldn't get username/password")
      logging.error("Couldn't get username/password")
      MatrixRoomCreatorUser.num_users_rooms_created += 1
      return

    # Log in as this current user
    self.login(start_syncing = False, log_request = True)
    # The login() method sets user_id and access_token
    if self.user_id is None or self.access_token is None:
      logging.error("Login failed for User [%s]" % self.username)
      MatrixRoomCreatorUser.num_users_rooms_created += 1
      return

    def username_to_userid(uname):
      uid = uname + ":" + self.matrix_domain
      if not uid.startswith("@"):
        uid = "@" + uid
      return uid

    my_rooms_info = rooms_for_users.get(self.username, [])
    #logging.info("User [%s] Found %d rooms to be created" % (self.username, len(my_rooms_info)))
    for room_info in my_rooms_info:
      room_name = room_info["name"]
      room_alias = room_name.lower().replace(" ", "-")
      usernames = room_info["users"]
      user_ids = list(map(username_to_userid, usernames))
      logging.info("User [%s] Creating room [%s] with %d users" % (self.username, room_name, len(user_ids)))
      # Actually create the room
      self.create_room(alias=room_alias, room_name=room_name, user_ids=user_ids)
      # Give the server a breather before we create the next one
      self.wait()

    # Logout this user so we can log in as the next guy
    self.logout()
    MatrixRoomCreatorUser.num_users_rooms_created += 1

    # Stop the load test after all users have been registered in the csv file
    if self.environment.web_ui is None and \
      MatrixRoomCreatorUser.num_users_rooms_created >= self.total_num_users:

      # Locust has an issue where sometimes it does not kill all internal greenlets.
      # As a workaround, sending the SIGTERM signal will cause a proper shutdown
      # instead of using the runner.quit method
      signal.raise_signal(signal.SIGTERM)
      #self.environment.runner.quit()
