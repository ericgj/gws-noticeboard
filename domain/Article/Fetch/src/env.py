import os
from google.oauth2 import service_account

from shared.util.env import assert_environ, load_json
from shared.adapter import pubsub, logging


# ------------------------------------------------------------------------------
# Environment variables: Domain
# ------------------------------------------------------------------------------


@assert_environ(["APP_SUBDOMAIN"])
def subdomain():
    return os.environ["APP_SUBDOMAIN"]


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


def service_account_file():
    """
    Note: this is not used, set GOOGLE_APPLICATION_CREDENTIALS instead
    """
    return os.environ.get("APP_SERVICE_ACCOUNT", None)


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


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------


def logging_client():
    return logging.client(service_account_credentials())


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
    log_type = context.get("$data","LogRecord") if log_type is None else log_type
    return logging.LogRecord(
        app_subdomain=subdomain(),
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
