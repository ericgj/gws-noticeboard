from hypothesis import given, settings

# import pytest

from main import _fetch_article
from test.util.fetch import url_examples


@given(url=url_examples())
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_runs_without_errors(url):
    _ = _fetch_article(url)
    assert True
