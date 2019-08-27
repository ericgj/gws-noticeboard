import os
import os.path
import json
from functools import wraps
import ruamel.yaml as yaml


def assert_environ(keys):
    def _assert_environ(fn):
        @wraps(fn)
        def __assert_environ(*args, **kwargs):
            for key in keys:
                assert (
                    key in os.environ
                ), "Missing required environment variable: %s" % (key,)
            return fn(*args, **kwargs)

        return __assert_environ

    return _assert_environ


def load_json(fname):
    data = None
    with open(fname, "r") as f:
        data = json.load(f)
    return data


def load_yaml(fname):
    data = None
    with open(fname, "r") as f:
        data = yaml.safe_load(f)
    return data


def load_json_fields(fname, fields=None):
    ret = None
    raw = {}
    with open(fname, "r") as f:
        raw = json.load(f)
    if fields is None:
        ret = raw
    else:
        ret = dict([(k, raw[k]) for k in raw if k in fields])
    return ret
