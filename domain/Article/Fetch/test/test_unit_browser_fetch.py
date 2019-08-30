from hypothesis import given, settings

# import pytest

import browser
from test.util.fetch import url_examples


@given(url=url_examples())
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch_runs_without_errors(url):
    _ = browser.fetch(url)
    assert True
