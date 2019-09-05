from dataclasses import dataclass
from typing import Union, Optional

from shared.model.article import FetchedArticle


@dataclass
class RequestArticle:
    url: str
    note: Optional[str] = None

    @classmethod
    def from_json(cls, d: dict) -> "RequestArticle":
        return cls(url=d["url"], note=d.get("note", None))

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "url": self.url, "note": self.note}


@dataclass
class SaveFetchedArticle:
    url: str
    article: FetchedArticle

    @classmethod
    def from_json(cls, d: dict) -> "SaveFetchedArticle":
        return cls(url=d["url"], article=FetchedArticle.from_json(d["article"]))

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "url": self.url,
            "article": self.article.to_json(),
        }


@dataclass
class SaveFetchArticleError:
    url: str
    error: Union[str, Exception]

    @classmethod
    def from_json(cls, d: dict) -> "SaveFetchArticleError":
        return cls(url=d["url"], error=d["error"])

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "url": self.url,
            "error": str(self.error),
        }


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
