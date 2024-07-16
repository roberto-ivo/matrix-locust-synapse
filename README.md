# **NOTE:** This project has moved to https://gitlab.futo.org/load-testing/matrix-locust.git


# Matrix load generation with Locust

This project provides Python classes and scripts for load testing
[Matrix](https://matrix.org/) servers using [Locust](https://locust.io/).

## Getting started

### Prerequisites

We assume that you already have your Matrix homeserver installed and
configured for testing.

* Your homeserver should be configured to allow registering new accounts
  without any kind of email verification or CAPTCHA etc.

* Either turn off rate limiting entirely, or increase your rate limits
  to allow the volume of traffic that you plan to produce, with some
  extra headroom just in case.

If you need help creating a reproducible configuration for your server,
have a look at [matrix-docker-ansible-deploy](https://github.com/spantaleev/matrix-docker-ansible-deploy)
for an Ansible playbook that can be used to install and configure Synapse,
Dendrite, and (soon!) Conduit, along with any required databases and other
homeserver accessories.

You also need [Locust](https://github.com/locustio/locust) and
[locust-plugins](https://github.com/SvenskaSpel/locust-plugins)
installed on the machine that you will be using to generate load
on your server.

### Generating users and rooms

Before you can use the Locust scripts to load your Matrix server, you
first need to generate usernames and passwords for your Locust users,
as well as the set of rooms where they will chat with each other.

First we generate the usernames and passwords.

```console
[user@host matrix-locust]$ python3 generate_users.py
```

This saves the usernames and passwords to a file called `users.csv`.

Next we need to decide what the rooms are going to look like in our test.
The `generate_rooms.py` script generates as many rooms as there are users
in `users.csv`.

```console
[user@host matrix-locust]$ python3 generate_rooms.py
```

The script decides how many users should be in each room according to an "80/20"
rule (aka a power law distribution), in an attempt to match real-world
human behavior.
Most rooms will be small -- only 2 or 3 users -- but there is a good
chance that there will be some room so big as to contain every single
user in the test.
Once the script has decided how big each room should be, it selects users
randomly from the population to fill up each room.
It saves the room names and the user-room assignments in the file `rooms.json`.

## Running the tests

The following examples show just a few things that we can do with Locust.

In fact, the user registration script and the room creation script (1 and 2 below)
were not originally intended to stress the server.

You may need to play around with the total number of users and the spawn rate
to find a configuration that your homeserver can handle.

1. Registering user accounts

```console
$ locust -f locust-register-users.py --headless --users 1000 --spawn-rate 1 --run-time 10m  --host https://YOUR_HOMESERVER/
```

2. Creating rooms

```console
$ locust -f locust-create-rooms.py --headless --users 1000 --spawn-rate 2 --run-time 10m  --host https://YOUR_HOMESERVER/
```

3. Accepting invites to join rooms

```console
$ locust -f locust-accept-invites.py --headless --users 1000 --spawn-rate 2 --run-time 10m  --host https://YOUR_HOMESERVER/
```

4. Normal chat activity -- Accepting any pending invites, sending messages, paginating rooms

```console
$ locust -f locust-run-users.py --headless --users 1000 --spawn-rate 5 --run-time 5m  --host https://YOUR_HOMESERVER/
```

### Running distributed / multi-worker tests

Tests that support running with multiple workers can be found in `matrix-locust/client_server`. `locust-run-users.py` test also supports running with multiple workers.

Example for running a test with multiple workers (worker amount defaults to the amount of available CPU threads):

```console
$ python run.py matrix-locust/client_server/register.py
```

### Running automated tests

This repository supports the ability to run automated tests. You can define test suites, which are JSON files that describes a series of tests along with its Locust parameters to run. Examples of test suites are provided in the `test-suites` directory.

There are also utility scripts (located in the `scripts` directory), but note that some of these scripts are dependent on a specific server setup.

Example for running multiple test suites:

```console
$ python3 run.py --host YOUR_HOMESERVER test-suites/synapse-250.json; sleep 60; python3 run.py --host YOUR_HOMESERVER test-suites/dendrite-250.json; sleep 60; python3 run.py --host YOUR_HOMESERVER test-suites/conduit-250.json
```

Note: For the automation scripts provided in this repository, you should not prefix the host argument with `https://`.

## Writing your own tests

The base class for interacting with a Matrix homeserver is [MatrixUser](./matrixuser.py).

For an example of a class that extends `MatrixUser` to generate traffic
like a real user, see [MatrixChatUser](./matrixchatuser.py).


