from dataclasses import dataclass
from typing import Union, Optional

from shared.model.article import FetchedArticle, FetchArticleError


@dataclass
class RequestArticle:
    url: str
    note: Optional[str] = None

    @classmethod
    def from_json(cls, d: dict) -> "RequestArticle":
        return cls(url=d["url"], note=d.get("note", None))

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "url": self.url, "note": self.note}

    def __str__(self):
        return '%s(url="%s")' % (self.__class__.__name__, self.url)


@dataclass
class SaveFetchedArticle:
    id: str
    url: str
    article: FetchedArticle

    @classmethod
    def from_json(cls, d: dict) -> "SaveFetchedArticle":
        return cls(
            id=d["id"], url=d["url"], article=FetchedArticle.from_json(d["article"])
        )

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "article": self.article.to_json(full=True),
        }

    def __str__(self):
        return '%s(id="%s", url="%s")' % (self.__class__.__name__, self.id, self.url)


@dataclass
class SaveFetchArticleError:
    id: str
    url: str
    error: FetchArticleError

    @classmethod
    def from_json(cls, d: dict) -> "SaveFetchArticleError":
        return cls(
            id=d["id"], url=d["url"], error=FetchArticleError.from_json(d["error"])
        )

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "error": self.error.to_json(),
        }

    def __str__(self):
        return '%s(id="%s", url="%s")' % (self.__class__.__name__, self.id, self.url)


Command = Union[RequestArticle, SaveFetchedArticle, SaveFetchArticleError]


def from_json(d: dict) -> Command:
    t = d.get("$type", None)
    if t == "RequestArticle":
        return RequestArticle.from_json(d)
    elif t == "SaveFetchedArticle":
        return SaveFetchedArticle.from_json(d)
    elif t == "SaveFetchArticleError":
        return SaveFetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown command: %s" % (t,))
