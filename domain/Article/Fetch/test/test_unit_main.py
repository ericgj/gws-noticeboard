from time import sleep
from unittest.mock import patch
from uuid import uuid4

from hypothesis import given, settings
import hypothesis.strategies as hyp

import pytest

from shared.adapter.pubsub import gcf_encoding
from shared.event.core import SavedNewLink
from shared.event.fetch import (
    FetchedArticle,
    FetchedArticleWithIssues,
    FailedFetchingArticle,
)

from main import fetch

from test.util.fetch import UNBLOCKED_URLS, WARNING_URLS, BLOCKED_URLS, UNKNOWN_URLS

PAUSE_INTERVAL = 5  # To avoid hypothesis DOS'ing sites... but makes testing slooow


@given(url=hyp.sampled_from(UNBLOCKED_URLS))
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_unblocked_urls_publishes_fetched_article(url):

    sleep(PAUSE_INTERVAL)

    event = SavedNewLink(id=str(uuid4()), url=url)
    message, ctx = gcf_encoding(event.to_json(), {})

    with patch("env.publish") as publish:
        fetch(message, ctx)

    publish.assert_called_once()
    assert_serialized_event(FetchedArticle, publish.call_args[0][0])


@given(url=hyp.sampled_from(WARNING_URLS))
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_warning_urls_publishes_fetched_article_with_issues(url):

    sleep(PAUSE_INTERVAL)

    event = SavedNewLink(id=str(uuid4()), url=url)
    message, ctx = gcf_encoding(event.to_json(), {})

    with patch("env.publish") as publish:
        fetch(message, ctx)

    publish.assert_called_once()
    assert_serialized_event(FetchedArticleWithIssues, publish.call_args[0][0])


@given(url=hyp.sampled_from(BLOCKED_URLS + UNKNOWN_URLS))
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_blocked_unknown_urls_publishes_failed_fetching_article_and_throws_error(
    url
):

    sleep(PAUSE_INTERVAL)

    event = SavedNewLink(id=str(uuid4()), url=url)
    message, ctx = gcf_encoding(event.to_json(), {})

    with patch("env.publish") as publish:
        with pytest.raises(Exception):
            fetch(message, ctx)

    publish.assert_called_once()
    assert_serialized_event(FailedFetchingArticle, publish.call_args[0][0])


def assert_serialized_event(klass, data):
    actual = data.get("$type", None)
    assert (
        klass.__name__ == actual
    ), "Serialized event $type is '%s', but should be '%s'" % (actual, klass.__name__)
    _ = klass.from_json(data)