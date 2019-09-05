from typing import Iterator

# Note: assumes datastore API
from google.cloud import datastore


class NotFoundError(Exception):
    def __init__(self, kind: str, params: dict):
        self.kind = kind
        self.params = params

    def __str__(self) -> str:
        strparams = ", ".join(["%s = %s" % (k, v) for k, v in self.params.items()])
        return "%s not found where %s" % (self.kind, strparams)


def zap_articles(client: datastore.Client):
    zap(client, "Article")


def requested_article_exists(client: datastore.Client, url: str) -> bool:
    try:
        find_key(client, "Article", url=url)
        return True
    except NotFoundError:
        return False


def zap(client: datastore.Client, kind: str):
    assert_test_environment(client)
    keys = list(select_keys(client, kind))
    client.delete_multi(keys)


def assert_test_environment(client: datastore.Client):
    parts = client.namespace.split("-")
    assert "test" in parts, (
        "It looks like you are not running in a test environment. Please check"
        "and try again! (Namespace = %s)" % (client.namespace,)
    )


def find_key(client: datastore.Client, kind: str, **params) -> str:
    return [r.key for r in find(client, kind, ["__key__"], **params)]


def find(
    client: datastore.Client, kind: str, _projection: Iterator[str] = (), **params
) -> str:
    query = client.query(kind=kind, projection=_projection)
    for (k, v) in params.items():
        query.add_filter(k, "=", v)
    try:
        return list(query.fetch(limit=1))[0]
    except IndexError:
        raise NotFoundError(kind=kind, params=params)


def select_keys(client: datastore.Client, kind: str) -> Iterator[datastore.key.Key]:
    return [r.key for r in select(client, kind, ["__key__"])]


def select(
    client: datastore.Client, kind: str, _projection: Iterator[str] = ()
) -> Iterator[datastore.key.Key]:
    query = client.query(kind=kind, projection=_projection)
    return list(query.fetch())
