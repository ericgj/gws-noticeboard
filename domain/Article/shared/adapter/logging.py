from contextlib import contextmanager
from datetime import datetime
from functools import wraps
import json
import logging
import sys
from time import time, gmtime
import traceback
from uuid import uuid4
from warnings import warn

import google.cloud.logging
from google.cloud.logging.resource import Resource

# import google.cloud.error_reporting

SCOPES = [
    "https://www.googleapis.com/auth/logging.write",
    #    "https://www.googleapis.com/auth/cloud-platform",
]

FORMATTER_ARGS = [None, None, "{"]


def client(credentials=None):
    return google.cloud.logging.Client(credentials=credentials)


""" Note: not currently used. 
def error_reporting_client(*, project, service=None, version=None, credentials=None):
    return google.cloud.error_reporting.Client(
        project=project, service=service, version=version, credentials=credentials
    )
"""


def init_logging(
    client, level=logging.INFO, resource_type=None, resource_labels=None, labels={}
):
    """
    Call this once at the top of your main program to log via Stackdriver. 
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    resource = (
        Resource(type=resource_type, labels=resource_labels)
        if resource_type is not None
        else None
    )
    handler = client.get_default_handler(resource=resource, labels=labels)
    handler.setFormatter(LogFormatter(*FORMATTER_ARGS))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def init_local_logging(level=logging.INFO, labels=None):
    """
    Call this once at the top of your main program to log locally. 
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    handler = logging.StreamHandler()
    handler.setFormatter(LocalLogFormatter(labels, *FORMATTER_ARGS))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def get_logger(name=None):
    """
    Convenience so you don't need to import base python logging module.
    """
    return logging.getLogger(name)


getLogger = get_logger


class LogFormatter(logging.Formatter):
    """
    Note we hook up a Formatter that saves built-in logging info as well as extra 
    data provided in logger methods to Stackdriver jsonPayload. Stackdriver detects 
    we are emitting a structured record automatically, it seems. I am following the 
    basic method outlined here (with quite a few enhancements):
    https://medium.com/google-cloud/python-and-stackdriver-logging-2ade460c90e3
    """

    def format(self, record):
        """ 
        Note: the log formatting string and "format style" is ignored here.
        We are not generating a log string but a dict. The message is formatted
        always according to python 3.x string-formatting style. Also, the
        pre-processing of message strings using %-style formatting against the
        args is disabled.

        The variables available in message strings are those in the final
        dict, which include both logging record fields (prefixed with log_),
        _and_ those passed in in the record.args.
        """

        # record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        # message = self.formatMessage(record)

        record_data = {
            "log_name": record.name,
            "log_level": record.levelname,
            "log_levelno": record.levelno,
            "log_asctime": record.asctime,
            "log_created": record.created,
            "log_pathname": record.pathname,
            "log_filename": record.filename,
            "log_module": record.module,
            "log_funcName": record.funcName,
            "log_lineno": record.lineno,
        }

        """ OMG logging are you serious ? """
        if isinstance(record.args, dict):
            data = record.args.copy()
        elif isinstance(record.args, tuple) and len(record.args) > 0:
            if isinstance(record.args[0], dict):
                data = record.args[0].copy()
            else:
                data = {"log_args": list(record.args)}
        else:
            data = {}

        data.update(record_data)
        data["message"] = record.msg.format(**data)
        return data


class LocalLogFormatter(LogFormatter):
    """
    If logging locally (not connected to Stackdriver), dump the structured record 
    to a json string in the shape of a Stackdriver log entry record.
    (If serialization fails, just dump the message field and drop a console warning.)
    """

    def __init__(self, labels=None, *args, **kwargs):
        super(LocalLogFormatter, self).__init__(*args, **kwargs)
        self._labels = {} if labels is None else labels

    def format(self, record):
        data = super(LocalLogFormatter, self).format(record)
        try:
            return json.dumps(stackdriver_log_entry(data, labels=self._labels))
        except Exception as e:
            warn("Error serializing log data, only logging message: %s" % (e,))
            return json.dumps(
                stackdriver_log_entry(
                    data, message=str(data.get("message", "")), labels=self._labels
                )
            )


def stackdriver_log_entry(data, message=None, labels=None, resource=None):
    rectime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    logtime = data.get("log_created", None)
    timestamp = (
        rectime
        if logtime is None
        else datetime(*gmtime(logtime)[:6]).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    message = data if message is None else message
    return {
        "insertId": str(uuid4()),
        "jsonPayload": {"message": data, "python_logger": data.get("log_name", "")},
        "logName": "local",
        "receiveTimestamp": rectime,
        "resource": {"type": "global", "labels": {}} if resource is None else resource,
        "labels": {} if labels is None else labels,
        "severity": data.get("log_level", ""),
        "timestamp": timestamp,
    }


# ------------------------------------------------------------------------------
# Instrumentation
# ------------------------------------------------------------------------------


@contextmanager
def log_elapsed(msg, logger, log_error="error", raise_error=False, context={}):
    def _build_context(secs, err=None):
        c = context.copy()
        c["log_type"] = context.get("log_type", "TimeElapsed")
        c["minutes"] = secs / 60
        c["seconds"] = secs
        c["milliseconds"] = secs * 1000
        if err is not None:
            c["error"] = err
        return c

    t0 = time()
    elapsed = 0

    try:
        yield
        elapsed = time() - t0
    except Exception as e:
        elapsed = time() - t0
        new_context = _build_context(elapsed, e)
        if log_error in ("debug", "info", "warning", "error", "fatal", "critical"):
            getattr(logger, log_error)(msg, new_context)
        if raise_error:
            raise

    new_context = _build_context(elapsed)
    logger.info(msg, new_context)


# ------------------------------------------------------------------------------
# Error Reporting
# ------------------------------------------------------------------------------


class RetryException(Exception):
    """ 
    Subclass and use this to always throw the error when using the log_errors
    decorator below. Throwing an error will signal to Cloud Functions to retry,
    if the function is configured to retry.
    """

    pass


def log_errors(
    logger,
    on_error=None,
    on_warning=None,
    warning_class=Warning,
    error_class=Exception,
    retry_error_class=RetryException,
):
    def _log_errors(fn):
        @wraps(fn)
        def __log_errors(*args, **kwargs):
            try:
                return fn(*args, **kwargs)

            except retry_error_class as e:
                data = _json_exc_info()
                data["log_type"] = e.__class__.__name__
                logger.error(str(e), data)
                raise

            except warning_class as w:
                data = _json_exc_info()
                data["log_type"] = w.__class__.__name__
                logger.warning(str(w), data)
                if on_warning is None:
                    raise
                else:
                    return on_warning(w)

            except error_class as e:
                data = _json_exc_info()
                data["log_type"] = e.__class__.__name__
                logger.error(str(e), data)
                if on_error is None:
                    raise
                else:
                    return on_error(e)

        return __log_errors

    return _log_errors


def _json_exceptions(data, exc_class=Exception):
    return dict(
        [
            (k, _json_exception(v) if isinstance(v, exc_class) else v)
            for (k, v) in data.items()
        ]
    )


def _json_exception(exc, type_key="$type"):
    if hasattr(exc, "to_json"):
        return exc.to_json()
    else:
        data = exc.__dict__
        data[type_key] = exc.__class__.__name__
        return data


def _json_exc_info(exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()
    exc_type, exc_value, exc_tb = exc_info
    return {
        "error": _json_exception(exc_value),
        "error_traceback": _json_traceback(exc_tb),
    }


def _json_traceback(exc_tb):
    frames = traceback.extract_tb(exc_tb)
    return [
        {"filename": f.filename, "name": f.name, "lineno": f.lineno, "line": f.line}
        for f in frames
    ]
