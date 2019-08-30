from dataclasses import dataclass
from typing import Union

from shared.model.article import Article


@dataclass
class FetchedArticle:
    id: str
    url: str
    article: Article

    @classmethod
    def from_json(cls, d: dict) -> "FetchedArticle":
        return cls(id=d["id"], url=d["url"], article=Article.from_json(d["article"]))

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "article": self.article.to_json(),
        }


@dataclass
class FailedFetchingArticle:
    id: str
    url: str
    error: Union[str, Exception]

    @classmethod
    def from_json(cls, d: dict) -> "FailedFetchingArticle":
        return cls(id=d["id"], url=d["url"], error=d["error"])

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "error": str(self.error),
        }


Command = Union[FetchedArticle, FailedFetchingArticle]


def from_json(d: dict) -> Command:
    t = d.get("$type", None)
    if t == "FetchedArticle":
        return FetchedArticle.from_json(d)
    if t == "FailedFetchingArticle":
        return FailedFetchingArticle.from_json(d)
    else:
        raise ValueError("Unknown event: %s" % (t,))
