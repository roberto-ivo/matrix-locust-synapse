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

# Open our list of users
user_reader = csv.DictReader(open("users.csv"))

# Find our user avatar images
avatars = []  
avatars_folder = "avatars"
avatar_files = glob.glob(os.path.join(avatars_folder, "*.png"))

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

################################################################################


class MatrixRegisterUser(MatrixUser):

  wait_time = between(1,3)
  num_registered_users = 0

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)


  @task
  def register_user(self):
    # Here we override the fancy distributed load generation stuff in MatrixUser,
    # because we need to make sure that each user is registered exactly once.
    # Nobody should be left out, and there's no point in attempting to register
    # the same user twice.

    # OTOH we're also kind of weird here because this User class doesn't really
    # represent just one human user.  It's just an agent that loads user info
    # from the CSV file, registers them, and then logs out.

    # Load the next user who needs to be registered
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
      return

    while True:
      # Register with the server to get a user_id and access_token
      self.register()
      # The register() method sets user_id and access_token

      if self.user_id is not None and self.access_token is not None:
        MatrixRegisterUser.num_registered_users += 1

        # FIXME Upload and set the user's avatar image
        # Set the user's display name
        self.set_displayname()

        # Log out the current user so we can register as the next one in the queue
        self.logout()
        break
      else:
        # Re-attempt user registration if failed (e.g. timeout)
        self.wait()

    # Stop the load test after all users have been registered in the csv file
    if self.environment.web_ui is None and \
      MatrixRegisterUser.num_registered_users >= self.total_num_users:

      # Locust has an issue where sometimes it does not kill all internal greenlets.
      # As a workaround, sending the SIGTERM signal will cause a proper shutdown
      # instead of using the runner.quit method
      signal.raise_signal(signal.SIGTERM)
      #self.environment.runner.quit()

