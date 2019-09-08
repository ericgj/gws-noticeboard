from typing import Optional, Tuple, Iterable

# Note: assumes datastore API
from google.cloud import datastore

from shared.model.article import (
    Article,
    RequestedArticle,
    FetchedArticle,
    FetchArticleError,
)


class NotFoundError(Exception):
    def __init__(self, kind: str, params: dict):
        self.kind = kind
        self.params = params

    def __str__(self) -> str:
        strparams = ", ".join(["%s = %s" % (k, v) for k, v in self.params.items()])
        return "%s not found where %s" % (self.kind, strparams)


def store_requested_article(
    client: datastore.Client, request: RequestedArticle, note: Optional[str] = None
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


def store_fetched_article(
    client: datastore.Client, id: str, url: str, article: FetchedArticle
) -> str:
    return store_article(client, article, id=id, url=url)


def store_fetch_article_error(
    client: datastore.Client, id: str, url: str, error: FetchArticleError
) -> str:
    return store_article(client, error, id=id, url=url)


def find_article_id(client, **params) -> str:
    return find_id(client, kind="Article", **params)


def store_article(
    client: datastore.Client,
    article: Article,
    id: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    data = article.to_json()
    if url is not None:
        data["url"] = url
    return store(client, data, kind="Article", id=id)


def store_article_note(client: datastore.Client, article_id: str, note: str) -> str:
    return store(
        client, {"note": note}, parent=["Article", article_id], kind="ArticleNote"
    )


# Datastore adapter layer


def find_id(client: datastore.Client, kind: str, **params) -> str:
    return find(client, kind, ["__key__"], **params).id


def find(
    client: datastore.Client, kind: str, _projection: Iterable[str] = (), **params
) -> str:
    query = client.query(kind=kind, projection=_projection)
    for (k, v) in params.items():
        query.add_filter(k, "=", v)
    try:
        return list(query.fetch(limit=1))[0]
    except IndexError:
        raise NotFoundError(kind=kind, params=params)


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
