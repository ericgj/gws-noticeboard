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


def gcf_adapter(decoder, metadata_decoder=None, encoding="utf-8"):
    def _decoded_base64(fn):
        @wraps(fn)
        def __decoded_base64(msg, *args, **kwargs):
            s = b64decode(msg["data"]).decode(encoding)
            value = json.loads(s)
            metadata = msg.get("attributes", {})
            return decoded(decoder, metadata_decoder)(fn)(
                value, metadata, *args, **kwargs
            )

        return __decoded_base64

    return _decoded_base64


def decoded(decoder, metadata_decoder=None):
    def _decoded(fn):
        @wraps(fn)
        def __decoded(value, metadata, *args, **kwargs):
            try:
                decoded = decoder(value)
            except Exception as e:
                raise DecodeFailure(_class_or_function_name(decoder), value, e)

            try:
                decoded_meta = (
                    metadata if metadata_decoder is None else metadata_decoder(metadata)
                )
            except Exception as e:
                raise DecodeFailure(
                    _class_or_function_name(metadata_decoder), metadata, e
                )
            return fn(decoded, decoded_meta, *args, **kwargs)

        return __decoded

    return _decoded


def _class_or_function_name(fn):
    if hasattr(fn, "__self__"):
        return fn.__self__.__name__
    elif hasattr(fn, "__name__"):
        return fn.__name__
    else:
        return str(fn)
