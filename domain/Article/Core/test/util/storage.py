from typing import Optional, Iterator, Tuple

# Note: assumes datastore API
from google.cloud import datastore

from shared.model import article


class NotFoundError(Exception):
    def __init__(self, kind: str, params: dict):
        self.kind = kind
        self.params = params

    def __str__(self) -> str:
        strparams = ", ".join(["%s = %s" % (k, v) for k, v in self.params.items()])
        return "%s not found where %s" % (self.kind, strparams)


def zap_articles(client: datastore.Client):
    zap(client, "Article")
    zap(client, "ArticleIssue")


##### PLEASE NOTE: these are duplicated from the actual adapter.storage.
##### They should not change too much, but be careful!!


def store_requested_article(
    client: datastore.Client,
    request: article.RequestedArticle,
    note: Optional[str] = None,
) -> Tuple[str, bool]:
    url = request.url
    try:
        id = find_article_id(client, url=url)
        if note is not None:
            _ = store_article_note(client, article_id=id, note=note)
        return (id, False)

    except NotFoundError:
        id = store_article(client, request)
        if note is not None:
            _ = store_article_note(client, article_id=id, note=note)
        return (id, True)


def store_article(
    client: datastore.Client,
    article: article.Article,
    id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    data = article.to_json()
    if url is not None:
        data["url"] = url
    return store(client, article.to_json(), kind="Article", id=id)


def store_article_note(client: datastore.Client, article_id: str, note: str) -> str:
    return store(
        client, {"note": note}, parent=["Article", article_id], kind="ArticleNote"
    )


######


def find_article_id(client, **params) -> str:
    return find_id(client, kind="Article", **params)


def find_article(client, **params) -> str:
    return find(client, kind="Article", **params)


def requested_article_exists(client: datastore.Client, url: str) -> bool:
    return article_with_url_exists(client, url)


def article_with_url_exists(client: datastore.Client, url: str) -> bool:
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


# Datastore adapter layer


def store(
    client: datastore.Client,
    data: dict,
    parent=[],
    kind: Optional[str] = None,
    id: Optional[str] = None,
) -> str:
    key = None
    kind = data.get("$type", None) if kind is None else kind
    if kind is None:
        raise ValueError("No kind specified")

    if id is None:
        key = client.allocate_ids(client.key(*parent, kind), 1)[0]
    else:
        key = client.key(*parent, kind, id)

    entity = datastore.Entity(key=key)
    entity.update(data)
    client.put(entity)
    return key.id


def find_id(client: datastore.Client, kind: str, **params) -> str:
    return find_key(client, kind, **params).id


def find_key(client: datastore.Client, kind: str, **params) -> datastore.Key:
    return [r.key for r in find(client, kind, ["__key__"], **params)]


def find(
    client: datastore.Client, kind: str, projection: Iterator[str] = (), **params
) -> str:
    query = client.query(kind=kind, projection=projection)
    for (k, v) in params.items():
        query.add_filter(k, "=", v)
    try:
        return list(query.fetch(limit=1))[0]
    except IndexError:
        raise NotFoundError(kind=kind, params=params)


def select_keys(client: datastore.Client, kind: str) -> Iterator[datastore.key.Key]:
    return [r.key for r in select(client, kind, ["__key__"])]


def select(
    client: datastore.Client, kind: str, projection: Iterator[str] = ()
) -> Iterator[datastore.key.Key]:
    query = client.query(kind=kind, projection=projection)
    return list(query.fetch())
