from base64 import b64decode
from functools import wraps
import json

from google.cloud import pubsub_v1


def publisher_client(creds=None):
    return pubsub_v1.PublisherClient(credentials=creds)


def create_topics(client, project_id, topics):
    project_path = client.project_path(project_id)
    existing = [t.name for t in client.list_topics(project_path)]
    for topic in topics:
        t = client.topic_path(project_id, topic)
        if t not in existing:
            client.create_topic(t)


def publish(client, project_id, topic, data):
    encoded = json.dumps(data).encode("utf-8")
    client.publish(client.topic_path(project_id, topic), encoded)


# ------------------------------------------------------------------------------
# Google Cloud Functions adapter
# ------------------------------------------------------------------------------


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


def gcf_adapter(decoder, encoding="utf-8"):
    def _decoded_base64(fn):
        @wraps(fn)
        def __decoded_base64(msg, *args, **kwargs):
            s = b64decode(msg["data"]).decode(encoding)
            # print(s)
            value = json.loads(s)
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
