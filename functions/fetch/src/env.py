import os
from google.oauth2 import service_account

from util.env import assert_environ, load_json
from adapter import pubsub


# ------------------------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------------------------


@assert_environ(["GCP_PROJECT"])
def project_id():
    return os.environ["GCP_PROJECT"]


def function_name():
    return os.environ.get("FUNCTION_NAME", function_target())


@assert_environ(["FUNCTION_TARGET"])
def function_target():
    return os.environ["FUNCTION_TARGET"]


def service_account_file():
    return os.environ.get("APP_SERVICE_ACCOUNT", None)


@assert_environ(["APP_ENV"])
def environment():
    return os.environ["APP_ENV"]


@assert_environ(["APP_PUBLISH_TOPIC"])
def publish_topic():
    return os.environ["APP_PUBLISH_TOPIC"]


# ------------------------------------------------------------------------------
# Service account
# ------------------------------------------------------------------------------


def service_account_info():
    file = service_account_file()
    return None if file is None else load_json(file)


def service_account_credentials(scopes=None):
    """
    Note: If no service account file specified, Google will try to use 
    GOOGLE_APPLICATION_CREDENTIALS
    """
    file = service_account_file()
    return (
        None
        if file is None
        else service_account.Credentials.from_service_account_file(file, scopes=scopes)
    )


# ------------------------------------------------------------------------------
# PubSub
# ------------------------------------------------------------------------------


def pubsub_client():
    return pubsub.publisher_client(service_account_credentials())


def publish(msg):
    return pubsub.publish(pubsub_client(), project_id(), publish_topic(), msg)
