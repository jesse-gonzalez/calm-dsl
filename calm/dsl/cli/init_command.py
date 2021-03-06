import click
import os
import json

from calm.dsl.config import init_config, get_default_user_config_file, set_config
from calm.dsl.db import get_db_handle
from calm.dsl.api import get_resource_api, update_client_handle, get_client_handle
from calm.dsl.store import Cache
from calm.dsl.init import init_bp
from calm.dsl.providers import get_provider_types

from .main import init, set
from calm.dsl.tools import get_logging_handle

LOG = get_logging_handle(__name__)


@init.command("dsl")
@click.option(
    "--ip",
    "-i",
    envvar="PRISM_SERVER_IP",
    default=None,
    help="Prism Central server IP or hostname",
)
@click.option(
    "--port",
    "-P",
    envvar="PRISM_SERVER_PORT",
    default=None,
    help="Prism Central server port number",
)
@click.option(
    "--username",
    "-u",
    envvar="PRISM_USERNAME",
    default=None,
    help="Prism Central username",
)
@click.option(
    "--password",
    "-p",
    envvar="PRISM_PASSWORD",
    default=None,
    help="Prism Central password",
)
@click.option("--project", "-pj", "project_name", help="Project name for entity")
def initialize_engine(ip, port, username, password, project_name):
    """Initializes the calm dsl engine"""

    set_server_details(ip, port, username, password, project_name)
    init_db()
    sync_cache()

    click.echo("\nHINT: To get started, follow the 3 steps below:")
    click.echo("1. Initialize an example blueprint DSL: calm init bp")
    click.echo(
        "2. Create and validate the blueprint: calm create bp --file HelloBlueprint/blueprint.py"
    )
    click.echo(
        "3. Start an application using the blueprint: calm launch bp HelloBlueprint --app_name HelloApp01 -i"
    )

    click.echo("\nKeep Calm and DSL On!\n")


def set_server_details(ip, port, username, password, project_name):

    if not (ip and port and username and password and project_name):
        click.echo("Please provide Calm DSL settings:\n")

    host = ip or click.prompt("Prism Central IP", default="")
    port = port or click.prompt("Port", default="9440")
    username = username or click.prompt("Username", default="admin")
    password = password or click.prompt("Password", default="", hide_input=True)
    project_name = project_name or click.prompt("Project", default="default")

    LOG.info("Checking if Calm is enabled on Server")
    # Get temporary client handle
    client = get_client_handle(host, port, auth=(username, password), temp=True)
    Obj = get_resource_api("services/nucalm/status", client.connection)
    res, err = Obj.read()

    if err:
        click.echo("[Fail]")
        raise Exception("[{}] - {}".format(err["code"], err["error"]))

    result = json.loads(res.content)
    service_enablement_status = result["service_enablement_status"]
    LOG.info(service_enablement_status)

    db_location = os.path.join(os.path.expanduser("~"), ".calm", "dsl.db")

    # Default log-level
    log_level = "INFO"

    # Default user config file
    user_config_file = get_default_user_config_file()

    LOG.info("Writing config to {}".format(user_config_file))
    init_config(host, port, username, password, project_name, db_location, log_level)
    LOG.info("Success")

    # Update client handle with new settings if no exception occurs
    update_client_handle(host, port, auth=(username, password))


def init_db():
    LOG.info("Creating local database")
    get_db_handle()
    LOG.info("Success")


def sync_cache():
    LOG.info("Updating Cache")
    Cache.sync()
    LOG.info("Success")


@init.command("bp")
@click.option(
    "--dir_name", "-d", default=os.getcwd(), help="Directory path for the blueprint"
)
@click.option(
    "--type",
    "-t",
    "provider_type",
    type=click.Choice(get_provider_types()),
    default="AHV_VM",
    help="Provider type",
)
def init_dsl_bp(dir_name, provider_type):
    """Creates a starting directory for blueprint"""
    service = "Hello"
    init_bp(service, dir_name, provider_type)


@set.command("config")
@click.option(
    "--ip",
    "-i",
    "host",
    envvar="PRISM_SERVER_IP",
    default=None,
    help="Prism Central server IP or hostname",
)
@click.option(
    "--port",
    "-P",
    envvar="PRISM_SERVER_PORT",
    default=None,
    help="Prism Central server port number",
)
@click.option(
    "--username",
    "-u",
    envvar="PRISM_USERNAME",
    default=None,
    help="Prism Central username",
)
@click.option(
    "--password",
    "-p",
    envvar="PRISM_PASSWORD",
    default=None,
    help="Prism Central password",
)
@click.option("--project", "-pj", "project_name", help="Project name for entity")
@click.option(
    "--db_file",
    "-d",
    "db_location",
    envvar="DATABASE_LOCATION",
    default=None,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Path to local database file",
)
@click.option("--log_level", "-l", default=None, help="Default log level")
@click.argument("config_file", default=get_default_user_config_file())
def _set_config(
    host, port, username, password, project_name, db_location, log_level, config_file
):
    """writes the configuration to config file"""

    set_config(
        host,
        port,
        username,
        password,
        project_name,
        db_location,
        log_level,
        config_file=config_file,
    )
