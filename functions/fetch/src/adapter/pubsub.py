from base64 import b64encode
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


def publish(client, topic, data):
    encoded = b64encode(json.dumps(data).encode("utf-8"))
    client.publish(topic, encoded)
