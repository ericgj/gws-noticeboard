from datetime import datetime
import os
from unittest.mock import patch

os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"
] = "secrets/test/service-accounts/article.json"

from hypothesis import given, settings
import pytest

from shared.adapter.pubsub import gcf_encoding
from shared.util.test import assert_serialized_event
from shared.command import core as core_command
from shared.event import core as core_event
from shared.util.url import standardized_url
from shared.model import article

from main import core
import env

from test.util.examples import (
    url_examples,
    requested_article_examples,
    fetched_article_examples,
    fetch_article_error_examples,
)
from test.util import storage as storage_util

TODAY = datetime.utcnow().date()


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

    assert storage_util.requested_article_exists(db, url=standardized_url(command.url))


@given(
    url=url_examples(), fetched_article_data=fetched_article_examples(dates_near=TODAY)
)
@settings(deadline=None, max_examples=3)
@pytest.mark.unit
def test_core_success_save_fetched_article_with_no_issues(url, fetched_article_data):
    db = env.storage_client()
    storage_util.zap_articles(db)

    id, _ = storage_util.store_requested_article(
        db, article.RequestedArticle(url=standardized_url(url))
    )

    command = core_command.SaveFetchedArticle.from_json(
        {"id": id, "url": url, "article": fetched_article_data}
    )
    attributes = {}
    message, ctx = gcf_encoding(command.to_json(), attributes)

    ret = None
    with patch("env.publish") as publish:
        ret = core(message, ctx)

    args = publish.call_args_list
    print(args)

    assert ret == ""
    publish.assert_called_once()
    assert_serialized_event(core_event.SavedFetchedArticle, args[0][0][0])

    actual = storage_util.find_article(db, url=standardized_url(url))
    assert actual.id == id
    _ = article.FetchedArticle.from_json(actual)


@given(url=url_examples(), fetched_article_data=fetched_article_examples())
@settings(deadline=None, max_examples=3)
@pytest.mark.unit
def test_core_success_save_fetched_article_with_issues(url, fetched_article_data):
    db = env.storage_client()
    storage_util.zap_articles(db)

    id, _ = storage_util.store_requested_article(
        db, article.RequestedArticle(url=standardized_url(url))
    )

    command = core_command.SaveFetchedArticle.from_json(
        {"id": id, "url": url, "article": fetched_article_data}
    )
    attributes = {}
    message, ctx = gcf_encoding(command.to_json(), attributes)

    ret = None
    with patch("env.publish") as publish:
        ret = core(message, ctx)

    args = publish.call_args_list
    print(args)

    assert ret == ""
    publish.assert_called()
    assert len(args) == 2
    assert_serialized_event(core_event.SavedFetchedArticle, args[0][0][0])
    assert_serialized_event(core_event.SavedArticleIssues, args[1][0][0])

    actual = storage_util.find_article(db, url=standardized_url(url))
    assert actual.id == id
    _ = article.FetchedArticle.from_json(actual)


@given(url=url_examples(), fetch_article_error_data=fetch_article_error_examples())
@settings(deadline=None, max_examples=3)
@pytest.mark.unit
def test_core_success_save_fetch_article_error(url, fetch_article_error_data):
    db = env.storage_client()
    storage_util.zap_articles(db)

    id, _ = storage_util.store_requested_article(
        db, article.RequestedArticle(url=standardized_url(url))
    )

    command = core_command.SaveFetchArticleError.from_json(
        {"id": id, "url": url, "error": fetch_article_error_data}
    )
    attributes = {}
    message, ctx = gcf_encoding(command.to_json(), attributes)

    ret = None
    with patch("env.publish") as publish:
        ret = core(message, ctx)

    assert ret == ""
    publish.assert_called_once()
    assert_serialized_event(core_event.SavedFetchArticleError, publish.call_args[0][0])

    actual = storage_util.find_article(db, url=standardized_url(url))
    assert actual.id == id
    _ = article.FetchArticleError.from_json(actual)


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
