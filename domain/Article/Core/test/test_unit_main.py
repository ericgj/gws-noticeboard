import os
from unittest.mock import patch

from hypothesis import given, settings
import pytest

from shared.adapter.pubsub import gcf_encoding
from shared.util.test import assert_serialized_event
from shared.command import core as core_command
from shared.event import core as core_event
from shared.util.url import standardized_url

from main import core
import env

from test.util.examples import requested_article_examples
from test.util import storage as storage_util

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "secrets/test/service-accounts/article.json"


@given(requested_article_data=requested_article_examples())
@settings(deadline=None, max_examples=3)
@pytest.mark.unit
def test_core_success_request_article(requested_article_data):
    db = env.storage_client()
    storage_util.zap_articles(db)

    command = core_command.RequestArticle.from_json(requested_article_data)
    attributes = {}
    message, ctx = gcf_encoding(command.to_json(), attributes)

    ret = None
    with patch("env.publish") as publish:
        ret = core(message, ctx)

    assert ret == ""
    publish.assert_called_once()
    assert_serialized_event(
        core_event.SavedNewRequestedArticle, publish.call_args[0][0]
    )

    storage_util.requested_article_exists(db, url=standardized_url(command.url))


""" Failure test -- not needed yet
@pytest.mark.unit
def test_core_failure_retry_example():
    event = SomeInputEventOrCommand(some=example_state)
    attributes = {}
    message, ctx = gcf_encoding(event.to_json(), attributes)

    ret = None
    with patch("env.publish") as publish:
        with pytest.raises(SomeRetryError):
            ret = fetch(message, ctx)

    assert ret == ""
    publish.assert_called_once()
    assert_serialized_event(SomeOutputFailureEvent, publish.call_args[0][0])
"""
