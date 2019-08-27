from hypothesis import given, settings

# import pytest

import browser
from test.util.fetch import fetch_article_examples


@given(cmd=fetch_article_examples())
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_runs_without_errors(cmd):
    _ = browser.fetch(cmd)
    assert True
