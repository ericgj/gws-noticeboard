from dataclasses import dataclass
from typing import Union, Optional

from shared.model.article import Article


@dataclass
class SavedNewLink:
    id: str
    url: str
    note: Optional[str] = None

    @classmethod
    def from_json(cls, d: dict) -> "SavedNewLink":
        return cls(id=d["id"], url=d["url"], note=d.get("note", None))

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "note": self.note,
        }


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


Event = Union[SavedNewLink, SavedArticle, SavedFetchArticleError]


def from_json(d: dict) -> Event:
    t = d.get("$type", None)
    if t == "SavedNewLink":
        return SavedNewLink.from_json(d)
    elif t == "SavedArticle":
        return SavedArticle.from_json(d)
    elif t == "SavedFetchArticleError":
        return SavedFetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown event: %s" % (t,))
