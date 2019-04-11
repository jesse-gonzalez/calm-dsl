"""Calm CLI

Usage:
  calm.py get blueprints [<name> ...]
  calm.py describe blueprint <name> [--json|--yaml]
  calm.py upload blueprint <name>
  calm.py launch blueprint <name>
  calm.py config [--server <ip:port>] [--username <username>] [--password <password>]
  calm.py (-h | --help)
  calm.py (-v | --version)

Options:
  -h --help                  Show this screen.
  -v --version               Show version.
  -s --server url            Prism Central URL in <ip:port> format
  -u --username username     Prism Central username
  -p --password password     Prism Central password
"""
import os
import json
import time
import warnings
import configparser
from functools import reduce
from docopt import docopt

from calm.dsl.utils.server_utils import get_api_client as _get_api_client, ping

# Defaults to be used if no config file exists.
PC_IP = "10.51.152.102"
PC_PORT = 9440
PC_USERNAME = "admin"
PC_PASSWORD = "***REMOVED***"

LOCAL_CONFIG_PATH = "config.ini"
GLOBAL_CONFIG_PATH = "~/.calm/config"


def get_api_client(pc_ip=PC_IP, pc_port=PC_PORT, username=PC_USERNAME, password=PC_PASSWORD):
    return _get_api_client(pc_ip=pc_ip, pc_port=pc_port, auth=(username, password))


def main():
    global PC_IP, PC_PORT, PC_USERNAME, PC_PASSWORD
    local_config_exists = os.path.isfile(LOCAL_CONFIG_PATH)
    global_config_exists = os.path.isfile(GLOBAL_CONFIG_PATH)

    if global_config_exists and not local_config_exists:
        file_path = GLOBAL_CONFIG_PATH
    else:
        file_path = LOCAL_CONFIG_PATH

    config = configparser.ConfigParser()
    config.read(file_path)
    if "SERVER" in config:
        PC_IP = config["SERVER"]["pc_ip"]
        PC_PORT = config["SERVER"]["pc_port"]
        PC_USERNAME = config["SERVER"]["pc_username"]
        PC_PASSWORD = config["SERVER"]["pc_password"]

    arguments = docopt(__doc__, version="Calm CLI v0.1.0")

    if arguments["config"]:
        if arguments["--server"]:
            [PC_IP, PC_PORT] = arguments["--server"].split(":")
        if arguments["--username"]:
            PC_USERNAME = arguments["--username"]
        if arguments["--password"]:
            PC_PASSWORD = arguments["--password"]

        config["SERVER"] = {
            "pc_ip": PC_IP,
            "pc_port": PC_PORT,
            "pc_username": PC_USERNAME,
            "pc_password": PC_PASSWORD
        }
        with open(file_path, "w") as configfile:
            config.write(configfile)

    if arguments["get"]:
        get_blueprint_list(arguments["<name>"])
    if arguments["launch"]:
        launch_blueprint(arguments["<name>"][0])


def get_blueprint_list(names):
    global PC_IP
    assert ping(PC_IP) is True
    client = get_api_client()

    params = {
        "length": 20,
        "offset": 0,
    }
    if names:
        search_strings = ["name==.*" + reduce(lambda acc, c: "{}[{}|{}]".
                          format(acc, c.lower(), c.upper()), name, "") + ".*" for name in names
                          ]
        params["filter"] = ",".join(search_strings)
    res, err = client.list(params=params)

    if not err:
        print(">> Blueprint List >>")
        print(json.dumps(res.json(), indent=4, separators=(",", ": ")))
        assert res.ok is True
    else:
        warnings.warn(UserWarning("Cannot fetch blueprints from {}".format(PC_IP)))


def launch_blueprint(blueprint_name):
    client = get_api_client()
    # find bp
    params = {
        "filter": "name=={};state!=DELETED".format(blueprint_name)
    }

    res, err = client.list(params=params)
    if err:
        print("[{}] - {}".format(err["code"], err["error"]))
        return

    response = res.json()
    entities = response.get("entities", None)
    blueprint = None
    if entities:
        if len(entities) != 1:
            print("More than one blueprint found - {}".format(entities))
            return

        print(">> {} found >>".format(blueprint_name))
        blueprint = entities[0]
        uuid = blueprint["metadata"]["uuid"]
    else:
        print(">>No blueprint found with name {} found >>".format(blueprint_name))
        return

    blueprint_spec = blueprint['spec']

    launch_payload = {
        "spec": {
            "application_name": "ExistingVMApp-{}".format(int(time.time())),
            "app_profile_reference": {
                "kind": "app_profile",
                "name": "{}".format(blueprint_spec['app_profile_list'][0]),
            },
            "resources": blueprint_spec['resources']
        },
    }

    res, err = client.launch(uuid, launch_payload)
    if not err:
        print(">> {} launched >>".format(blueprint_name))
        print(json.dumps(res.json(), indent=4, separators=(",", ": ")))
    else:
        print("[{}] - {}".format(err["code"], err["error"]))
        return

    # Poll every 10 seconds on the app status, for 5 mins
    maxWait = 5 * 60
    count = 0
    while count < maxWait:
        # call status api
        count += 10
        time.sleep(10)


if __name__ == "__main__":
    main()
