from dataclasses import dataclass
from typing import Union

from shared.model import article


@dataclass
class SucceededFetchingArticle:
    id: str
    url: str
    article: article.Article

    @classmethod
    def from_json(cls, d: dict) -> "SucceededFetchingArticle":
        return cls(id=d["id"], url=d["url"], article=article.from_json(d["article"]))

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
class SucceededFetchingArticleWithIssues(SucceededFetchingArticle):
    pass


@dataclass
class FailedFetchingArticle:
    id: str
    url: str
    error: article.FetchArticleError

    @classmethod
    def from_error(cls, id: str, url: str, error: Exception) -> "FailedFetchingArticle":
        return cls(id=id, url=url, error=article.FetchArticleError.from_error(error))

    @classmethod
    def from_json(cls, d: dict) -> "FailedFetchingArticle":
        return cls(
            id=d["id"],
            url=d["url"],
            error=article.FetchArticleError.from_json(d["error"]),
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


Event = Union[
    SucceededFetchingArticle, SucceededFetchingArticleWithIssues, FailedFetchingArticle
]


def from_json(d: dict) -> Event:
    t = d.get("$type", None)
    if t == "SucceededFetchingArticle":
        return SucceededFetchingArticle.from_json(d)
    if t == "SucceededFetchingArticleWithIssues":
        return SucceededFetchingArticleWithIssues.from_json(d)
    if t == "FailedFetchingArticle":
        return FailedFetchingArticle.from_json(d)
    else:
        raise ValueError("Unknown event: %s" % (t,))
