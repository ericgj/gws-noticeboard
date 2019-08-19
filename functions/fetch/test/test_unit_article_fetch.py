from hypothesis import given, settings

from model.article import Article
from test.util.fetch import request_examples


@given(request=request_examples())
@settings(deadline=None)
def test_(request):
    _ = Article.fetch(request)
    assert True
