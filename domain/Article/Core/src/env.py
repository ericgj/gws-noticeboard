import os

import google.cloud.datastore

# Note: eventually put these in librar(ies)

from shared.adapter import pubsub, logging
from shared.util.env import assert_environ


# ------------------------------------------------------------------------------
# Environment variables: Domain
# ------------------------------------------------------------------------------


@assert_environ(["APP_SUBDOMAIN"])
def subdomain():
    return os.environ["APP_SUBDOMAIN"]


@assert_environ(["APP_SUBDOMAIN_NAMESPACE"])
def subdomain_namespace():
    return os.environ["APP_SUBDOMAIN_NAMESPACE"]


@assert_environ(["APP_SERVICE"])
def service():
    return os.environ["APP_SERVICE"]


@assert_environ(["APP_ENV"])
def environment():
    return os.environ["APP_ENV"]


def app_state():
    return os.environ.get("APP_STATE", None)


@assert_environ(["APP_PUBLISH_TOPIC"])
def publish_topic():
    return os.environ["APP_PUBLISH_TOPIC"]


@assert_environ(["APP_SUBSCRIBE_TOPIC"])
def subscribe_topic():
    return os.environ["APP_SUBSCRIBE_TOPIC"]


def logging_level():
    return os.environ.get("APP_LOGGING_LEVEL", "INFO").upper()


def remote_logging():
    """
    Note: turn this switch off to prevent undue Stackdriver logging in unit tests
    """
    return os.environ.get("APP_LOGGING_REMOTE", None) == "1"


def local_logging():
    return not remote_logging()


# ------------------------------------------------------------------------------
# Environment variables: Runtime
# ------------------------------------------------------------------------------


@assert_environ(["GCP_PROJECT"])
def project_id():
    return os.environ["GCP_PROJECT"]


def function_name():
    return os.environ.get("FUNCTION_NAME", function_target())


@assert_environ(["FUNCTION_TARGET"])
def function_target():
    return os.environ["FUNCTION_TARGET"]


def service_account_credentials():
    return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", None)


# ------------------------------------------------------------------------------
# PubSub
# ------------------------------------------------------------------------------


def pubsub_client():
    return pubsub.publisher_client()


def publish(msg):
    return pubsub.publish(pubsub_client(), project_id(), publish_topic(), msg)


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------


def logging_client():
    return logging.client()


def init_logging():
    if local_logging():
        logging.init_local_logging(logging_level())
        return

    try:
        logging.init_logging(logging_client(), logging_level())
        return

    except Exception as e:
        logging.init_local_logging(logging_level())
        logger = logging.get_logger(__name__)
        logger.warning(
            "Note: unable to connect to Stackdriver logging, logging locally. "
            "(Error: {error})",
            log_record(error=e),
        )
        return


def get_logger(name):
    return logging.get_logger(name)


def log_record(log_type=None, **context) -> dict:
    log_type = context.get("$data", "LogRecord") if log_type is None else log_type
    return logging.LogRecord(
        app_subdomain=subdomain(),
        app_subdomain_namespace=subdomain_namespace(),
        app_service=service(),
        app_environment=environment(),
        app_state=app_state(),
        app_publish_topic=publish_topic(),
        app_subscribe_topic=subscribe_topic(),
    ).with_context(log_type, context)


def log_elapsed(msg, logger, context={}, **kwargs):
    """ 
    Note: context manager for logging elapsed time
    """
    return logging.log_elapsed(msg, logger, log_record, context=context, **kwargs)


def log_errors(logger, *args, **kwargs):
    """ 
    Note: decorator for logging any unhandled errors
    """
    return logging.log_errors(logger, log_record, *args, **kwargs)


# ------------------------------------------------------------------------------
# Datastore
# ------------------------------------------------------------------------------


def storage_client() -> google.cloud.datastore.Client:
    return google.cloud.datastore.Client(namespace=subdomain_namespace())
