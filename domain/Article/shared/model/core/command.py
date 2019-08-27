from dataclasses import dataclass
from typing import Union, Optional

from shared.model.article import Article


@dataclass
class SaveLink:
    url: str
    note: Optional[str] = None

    @classmethod
    def from_json(cls, d: dict) -> "SaveLink":
        return cls(url=d["url"], note=d.get("note", None))

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "url": self.url, "note": self.note}


@dataclass
class SaveArticle:
    url: str
    article: Article

    @classmethod
    def from_json(cls, d: dict) -> "SaveArticle":
        return cls(url=d["url"], article=Article.from_json(d["article"]))

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


Command = Union[SaveLink, SaveArticle, SaveFetchArticleError]


def from_json(d: dict) -> Command:
    t = d.get("$type", None)
    if t == "SaveLink":
        return SaveLink.from_json(d)
    elif t == "SaveArticle":
        return SaveArticle.from_json(d)
    elif t == "SaveFetchArticleError":
        return SaveFetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown command: %s" % (t,))
