import os
from hypothesis import given, settings

import pytest

# temporary
os.environ["APP_SUBDOMAIN"] = "Article"
os.environ["APP_SERVICE"] = "Fetch"
os.environ["APP_ENV"] = "test"
os.environ["APP_STATE"] = ""
os.environ["APP_PUBLISH_TOPIC"] = "article.fetch.events--test"
os.environ["APP_SUBSCRIBE_TOPIC"] = "article.core.events--test"

from shared.model.article import ArticleIssues
from main import _fetch_article
import env

from test.util.fetch import url_examples

logger = env.get_logger(__name__)


@given(url=url_examples())
@settings(deadline=None)
@pytest.mark.skip(reason="temporary")
def test_fetch_runs_without_errors(url):
    try:
        article = _fetch_article(url)
        article.validate()

    except ArticleIssues as w:
        logger.warning(w, extra=env.log_record(error=w.to_json()))

    assert True
