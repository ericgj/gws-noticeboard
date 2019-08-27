from datetime import date

from hypothesis import given

from shared.model.article import Article
from test.util.fetch import article_data_examples

TODAY = date.today()


@given(data=article_data_examples(dates_near=TODAY))
def test_decode_encode(data):
    decoded = Article.from_json(data)
    encoded = decoded.to_json()
    for (k, v) in data.items():
        assert encoded[k] == v
