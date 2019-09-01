from dataclasses import dataclass, asdict
from functools import wraps
import json
import logging
import sys
import traceback
from typing import Optional
from warnings import warn

import google.cloud.logging

SCOPES = ["https://www.googleapis.com/auth/logging.write"]

FORMATTER_ARGS = [None, None, "{"]


def client(credentials=None):
    return google.cloud.logging.Client(credentials=credentials)


def init_logging(client, level=logging.INFO):
    """
    Call this once at the top of your main program to log via Stackdriver. 
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    handler = client.get_default_handler()
    handler.setFormatter(LogFormatter(*FORMATTER_ARGS))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def init_local_logging(level=logging.INFO):
    """
    Call this once at the top of your main program to log locally. 
    """
    if isinstance(level, str):
        level = getattr(logging, level)
    handler = logging.StreamHandler()
    handler.setFormatter(LocalLogFormatter(*FORMATTER_ARGS))
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
            "log_asctime": record.asctime,
            "log_created": record.created,
            "log_pathname": record.pathname,
            "log_filename": record.filename,
            "log_module": record.module,
            "log_funcName": record.funcName,
            "log_lineno": record.lineno,
            "log_msg": str(record.msg),
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
        data["message"] = record.message.format(**data)
        return data


class LocalLogFormatter(LogFormatter):
    """
    If logging locally (not connected to Stackdriver), dump the structured record 
    to a json string if possible, otherwise just the message field and drop
    a console warning.
    """

    def format(self, record):
        data = super(LocalLogFormatter, self).format(record)
        try:
            return json.dumps(data)
        except Exception as e:
            warn("Error serializing log data, only logging message: %s" % (e,))
            return json.dumps({"message": str(data["message"])})


# ------------------------------------------------------------------------------
# Log Record
# ------------------------------------------------------------------------------


@dataclass
class LogRecord:
    subdomain: str
    service: str
    environment: str
    publish_topic: str
    subscribe_topic: Optional[str]
    app_state: Optional[str]

    def with_context(self, ctx: dict, key: str = "context") -> dict:
        data = self.to_json()
        data.update({key: _json_exceptions(ctx)})
        return data

    def __call__(self, **ctx) -> dict:
        return self.with_context(ctx)

    def to_json(self) -> dict:
        data = asdict(self)
        data.update({"$type": self.__class__.__name__})
        return data


def log_errors(logger, log_record, exc_class=Exception):
    def _log_errors(fn):
        @wraps(fn)
        def __log_errors(*args, **kwargs):
            try:
                fn(*args, **kwargs)
            except exc_class as e:
                logger.error(e, log_record(**_json_exc_info()))
                raise e from None

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
    data = exc.__dict__
    data[type_key] = exc.__class__.__name__
    return data


def _json_exc_info(exc_info=None, type_key="$type"):
    if exc_info is None:
        exc_info = sys.exc_info()
    exc_type, exc_value, exc_tb = exc_info
    return {
        type_key: exc_type.__name__ if hasattr(exc_type, "__name__") else str(exc_type),
        "value": _json_exception(exc_value),
        "traceback": _json_traceback(exc_tb),
    }


def _json_traceback(exc_tb):
    frames = traceback.extract_tb(exc_tb)
    return [
        {"filename": f.filename, "name": f.name, "lineno": f.lineno, "line": f.line}
        for f in frames
    ]
