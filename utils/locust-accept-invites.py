#!/bin/env python3

import csv
import os
import sys
import glob
import random

import json
import logging

from locust import task, FastHttpUser, between, constant, TaskSet
from locust import events
from locust.runners import MasterRunner, WorkerRunner
from locust_plugins.csvreader import CSVDictReader


import gevent

from matrixuser import MatrixUser

# Preflight ###############################################

# Open our list of users
user_reader = csv.DictReader(open("users.csv"))

# Scream bloody murder if someone tries to run this distributed
@events.init.add_listener
def on_locust_init(environment, **_kwargs):
  if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, WorkerRunner):
    print("Error: This script does not support distributed load generation at this time.\nPlease run this in single-process mode without --master or --worker.")
    sys.exit(1)

###########################################################


class MatrixInviteAcceptorUser(MatrixUser):

  wait_time = between(1,3)


  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)


  @task
  def accept_invites(self):
    # Load the next user who needs to be logged-in
    try:
      user_dict = next(user_reader)
    except StopIteration:
      gevent.sleep(999999)
      return

    self.username = user_dict["username"]
    self.password = user_dict["password"]

    # First, sanity check that we should be here
    if self.username is None or self.password is None:
      logging.error("No username or password")
      self.environment.runner.quit()
      return

    # Log in
    self.login(start_syncing = False, log_request = True)

    # Call /sync exactly once to get our list of invited rooms
    self.sync()

    # Wait a bit before we try to start accepting invites
    self.wait()

    # self.invited_room_ids set is modified by the MatrixUser class after joining a room
    rooms_to_join = self.invited_room_ids.copy()

    #logging.info("User [%s] has %d pending invites" % (self.username, len(self.invited_room_ids)))
    for room_id in rooms_to_join:
      # Somehow null room ids are added to the list?
      if room_id is None:
        continue
      # Pretend that the user is looking at the invitation and deciding whether to accept
      delay = random.expovariate(1.0 / 5.0)
      gevent.sleep(delay)
      # Now accept the invite
      room_id = self.join_room(room_id)

    self.logout()
