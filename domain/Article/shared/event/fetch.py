from dataclasses import dataclass
from typing import Union, Iterator

from shared.model.article import Article, ArticleIssue


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
class FetchedArticleWithIssues:
    id: str
    url: str
    article: Article
    issues: Iterator[ArticleIssue]

    @classmethod
    def from_json(cls, d: dict) -> "FetchedArticleWithIssues":
        return cls(
            id=d["id"],
            url=d["url"],
            article=Article.from_json(d["article"]),
            issues=[ArticleIssue.from_json(issue) for issue in d["issues"]],
        )

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "id": self.id,
            "url": self.url,
            "article": self.article.to_json(),
            "issues": [issue.to_json() for issue in self.issues],
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
