import os
from test.adapter import pubsub
from test.util.fetch import fetch_article_data_examples

from hypothesis import given, settings

PROJECT_ID = 'gws-noticeboard'
FUNCTION_NAME = 'article_fetch_test'
SUB_TOPIC = 'article-fetch-test'
PUB_TOPIC = 'article-core-test'


@given(reqdata=fetch_article_data_examples())
@settings(deadline=None, max_examples=1)
def test_(reqdata):
    def _confirm(respdata):
        print(respdata)
        # assert False
       
    init_environ()
    with temporary_subscription() as sub:
        trigger(reqdata)
        sub(_confirm).result(timeout=20)


def init_environ():
    """ Note this service account has editor access to all topics/subs """
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'secrets/test/service-accounts/project.json'

def trigger(data):
    client = pubsub.publisher_client()
    pubsub.publish(client, PROJECT_ID, SUB_TOPIC, data)

def temporary_subscription():
    return pubsub.TemporarySubscription(
        client = pubsub.subscriber_client(),
        project=PROJECT_ID,
        topic=PUB_TOPIC
    )

