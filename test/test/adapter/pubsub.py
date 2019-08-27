from functools import wraps
import json
from time import sleep
from uuid import uuid4

from google.cloud import pubsub_v1


def publisher_client(credentials=None):
    return pubsub_v1.PublisherClient(credentials=credentials)


def subscriber_client(credentials=None):
    return pubsub_v1.SubscriberClient(credentials=credentials)


def publish(client, project, topic, data):
    encoded = json.dumps(data).encode("utf-8")
    client.publish(client.topic_path(project,topic), encoded)


class TemporarySubscription:
    def __init__(self, *, client, project, topic):
        self._client = client
        self._project = project
        self._topic = topic
        self._sub = "X-" + str(uuid4())  # "X-" to ensure sub name starts with alpha

    def __enter__(self):
        sub_path = self._client.subscription_path(self._project, self._sub)
        topic_path = self._client.topic_path(self._project, self._topic)
        self._client.create_subscription(sub_path, topic_path)
        sleep(1)
        return Subscriber(self._client, sub_path)

    def __exit__(self, exctype, exc, tb):
        sub_path = self._client.subscription_path(self._project, self._sub)
        self._client.delete_subscription(sub_path)


class Subscriber():
    def __init__(self, client, path):
        self._client = client
        self._path = path

    def __call__(self, callback, timeout=60):
        return self._client.subscribe(self._path, _wrap_callback(callback))


def _wrap_callback(fn):
    @wraps(fn)
    def _wrap(message):
        try:
            print(message.data)
            payload = json.loads(message.data.decode("utf8"))
            fn(payload)
            message.ack()
        except Exception as e:
            message.ack()
            raise e

    return _wrap
