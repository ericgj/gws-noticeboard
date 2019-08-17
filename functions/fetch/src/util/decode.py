from functools import wraps
from base64 import b64decode


class DecodeFailure(Exception):
    def __init__(self, klass, value, error):
        self.klass = klass
        self.value = value
        self.error = error

    def __str__(self):
        return "Unable to decode to %s: %s\n  from %s" % (
            self.klass,
            self.error,
            self.value,
        )


def decoded_base64(decoder, encoding="utf-8"):
    def _decoded_base64(fn):
        @wraps(fn)
        def __decoded_base64(raw, *args, **kwargs):
            value = b64decode(raw).decode(encoding)
            return decoded(decoder)(fn)(value, *args, **kwargs)

        return __decoded_base64

    return _decoded_base64


def decoded(decoder):
    def _decoded(fn):
        @wraps(fn)
        def __decoded(value, *args, **kwargs):
            try:
                decoded = decoder(value)
            except Exception as e:
                raise DecodeFailure(_class_or_function_name(decoder), value, e)
            return fn(decoded, *args, **kwargs)

        return __decoded

    return _decoded


def _class_or_function_name(fn):
    if hasattr(fn, "__self__"):
        return fn.__self__.__name__
    elif hasattr(fn, "__name__"):
        return fn.__name__
    else:
        return str(fn)
