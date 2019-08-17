import os
from google.oauth2 import service_account

from util.env import assert_environ, load_json


# ------------------------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------------------------


def service_account_file():
    return os.environ.get("SERVICE_ACCOUNT", None)


@assert_environ(["GCP_PROJECT"])
def project_id():
    return os.environ["GCP_PROJECT"]


@assert_environ(["FUNCTION_NAME"])
def function_name():
    return os.environ["FUNCTION_NAME"]


@assert_environ(["ENV"])
def environment():
    return os.environ["ENV"]


# ------------------------------------------------------------------------------
# Service account
# ------------------------------------------------------------------------------


def service_account_info():
    file = service_account_file()
    return None if file is None else load_json(file)


def service_account_credentials(scopes=None):
    file = service_account_file()
    return (
        None
        if file is None
        else service_account.Credentials.from_service_account_file(file, scopes=scopes)
    )


# ------------------------------------------------------------------------------
# PubSub
# ------------------------------------------------------------------------------


def pubsub_topic():
    return "{}".format(function_name())
