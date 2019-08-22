from hypothesis import given, settings

import pytest

from adapter import browser
from test.util.fetch import request_examples


@given(request=request_examples())
@settings(deadline=None)
@pytest.mark.skip(reason="temporary")
def test_fetch_runs_without_errors(request):
    _ = browser.fetch(request)
    assert True
