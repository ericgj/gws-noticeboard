from dataclasses import dataclass
from typing import Union

from shared.model.article import Article


@dataclass
class SavedNewRequestedArticle:
    id: str
    url: str

    @classmethod
    def from_json(cls, d: dict) -> "SavedNewRequestedArticle":
        return cls(id=d["id"], url=d["url"])

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "id": self.id, "url": self.url}


@dataclass
class SavedArticle:
    id: str
    url: str
    article: Article

    @classmethod
    def from_json(cls, d: dict) -> "SavedArticle":
        return cls(id=d["id"], url=d["url"], article=Article.from_json(d["article"]))

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "article": self.article.to_json(),
        }


@dataclass
class SavedFetchArticleError:
    id: str
    url: str
    error: Union[str, Exception]

    @classmethod
    def from_json(cls, d: dict) -> "SavedFetchArticleError":
        return cls(id=d["id"], url=d["url"], error=d["error"])

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "error": str(self.error),
        }


Event = Union[SavedNewRequestedArticle, SavedArticle, SavedFetchArticleError]


def from_json(d: dict) -> Event:
    t = d.get("$type", None)
    if t == "SavedNewRequestedArticle":
        return SavedNewRequestedArticle.from_json(d)
    elif t == "SavedArticle":
        return SavedArticle.from_json(d)
    elif t == "SavedFetchArticleError":
        return SavedFetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown event: %s" % (t,))
