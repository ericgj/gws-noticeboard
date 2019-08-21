from datetime import date

from hypothesis import given, settings

# import pytest

from model.article import Article
from test.util.fetch import request_examples, article_data_examples

TODAY = date.today()


@given(request=request_examples())
@settings(deadline=None)
# @pytest.mark.skip(reason="temporary")
def test_fetch(request):
    _ = Article.fetch(request)
    assert True


@given(data=article_data_examples(dates_near=TODAY))
def test_decode_encode(data):
    decoded = Article.from_json(data)
    encoded = decoded.to_json()
    for (k, v) in data.items():
        assert encoded[k] == v
