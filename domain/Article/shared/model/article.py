from datetime import date
from typing import List, Optional, Iterator, Union
from dataclasses import dataclass

import shared.util.date_ as date_
from shared.util.string_ import ellipsis

# ------------------------------------------------------------------------------
# REQUESTED ARTICLE
# ------------------------------------------------------------------------------


@dataclass
class RequestedArticle:
    url: str

    @classmethod
    def from_json(cls, d: dict) -> "RequestedArticle":
        return cls(url=d["url"])

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "url": self.url}


# ------------------------------------------------------------------------------
# FETCHED ARTICLE
# ------------------------------------------------------------------------------

MIN_EXPECTED_SIZE = 1500


@dataclass
class FetchedArticle:
    title: str
    authors: List[str]
    encoding: str
    raw_html: str
    text: str
    html: str
    publish_date: Optional[date] = None
    summary: Optional[str] = None
    site_name: Optional[str] = None

    @classmethod
    def from_json(cls, d: dict) -> "FetchedArticle":
        return cls(
            site_name=d.get("site_name", None),
            title=d["title"],
            authors=list(d["authors"]),
            summary=d.get("summary", None),
            encoding=d["encoding"],
            raw_html=d["raw_html"],
            text=d["text"],
            html=d["html"],
            publish_date=(
                None
                if d.get("publish_date", None) is None
                else date_.decode(d["publish_date"])
            ),
        )

    def to_json(self, full=False) -> dict:
        return {
            "$type": self.__class__.__name__,
            "site_name": self.site_name,
            "title": self.title,
            "authors": self.authors,
            "summary": (
                ellipsis(self.summary)
                if not full and self.summary is not None
                else self.summary
            ),
            "encoding": self.encoding,
            "raw_html": ellipsis(self.raw_html) if not full else self.raw_html,
            "text": ellipsis(self.text) if not full else self.text,
            "html": ellipsis(self.html) if not full else self.html,
            "publish_date": (
                None if self.publish_date is None else date_.encode(self.publish_date)
            ),
        }

    def first_author(self) -> Optional[str]:
        return None if len(self.authors) == 0 else self.authors[0]

    def validate(self):
        issues = []
        issues.extend(self.validate_length())
        issues.extend(self.validate_publish_date())
        # potentially more checks...

        if len(issues) > 0:
            raise ArticleIssues(issues=issues, article=self)

    def validate_length(self):
        issues = []
        size = len(self.html)
        if size < MIN_EXPECTED_SIZE:
            issues.append(ArticleIssueShort(size))
        return issues

    def validate_publish_date(self):
        issues = []
        if self.publish_date is None:
            issues.append(ArticleIssueMissing("publish date"))
        return issues


class ArticleIssues(Warning):
    def __init__(self, issues: "Iterator[ArticleIssue]", article: "FetchedArticle"):
        self.issues = issues
        self.article = article

    def __str__(self) -> str:
        n = len(self.issues)
        title = self.article.title
        return "Article '{title}' had {n} potential issue{plural}".format(
            title=title if len(title) < 40 else title[0:37] + "...",
            n=n,
            plural="s" if n > 1 else "",
        )

    def to_json(self, full: bool = False) -> dict:
        return {
            "$type": self.__class__.__name__,
            "message": str(self),
            "issues": [issue.to_json() for issue in self.issues],
            "article": self.article.to_json(full=full),
        }


class ArticleIssue:
    @classmethod
    def from_json(cls, d: dict) -> "ArticleIssue":
        typ = d.get("$type", None)
        if typ == "ArticleIssueShort":
            return ArticleIssueShort.from_json(d)
        elif typ == "ArticleIssueMissing":
            return ArticleIssueMissing.from_json(d)
        else:
            raise ValueError("Unknown ArticleIssue subclass %s" % (typ,))

    def to_json(self) -> dict:
        typ = self.__class__.__name__
        msg = str(self)
        data = self.__dict__
        data.update({"$type": typ, "message": msg})
        return data


class ArticleIssueShort(ArticleIssue):
    @classmethod
    def from_json(cls, d: dict) -> "ArticleIssueShort":
        return cls(size=d["size"])

    def __init__(self, size: int, ignored: bool = False):
        self.size = size
        self.ignored = ignored

    def __str__(self) -> str:
        return (
            "Article seems short ({size} characters). "
            "The parser may have failed to detect the body of the article, "
            "or the full article may be paywalled."
        ).format(size=self.size)


class ArticleIssueMissing(ArticleIssue):
    @classmethod
    def from_json(cls, d: dict) -> "ArticleIssueMissing":
        return cls(field=d["field"])

    def __init__(self, field: str, ignored: bool = False):
        self.field = field
        self.ignored = ignored

    def __str__(self) -> str:
        return (
            "Article seems to be missing {field}. "
            "The metadata parser may have failed to extract it from the article. "
        ).format(field=self.field)


# ------------------------------------------------------------------------------
# FETCH ARTICLE ERROR
# ------------------------------------------------------------------------------


@dataclass
class FetchArticleError:
    error_type: str
    error_message: str

    @classmethod
    def from_error(cls, error: Exception) -> "FetchArticleError":
        return cls(error_type=error.__class__.__name__, error_message=str(error))

    @classmethod
    def from_json(cls, d: dict) -> "FetchArticleError":
        return cls(error_type=d["error_type"], error_message=d["error_message"])

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


Article = Union[RequestedArticle, FetchedArticle, FetchArticleError]


def from_json(d: dict) -> Article:
    t = d.get("$type", None)
    if t == "RequestedArticle":
        return RequestedArticle.from_json(d)
    elif t == "FetchedArticle":
        return FetchedArticle.from_json(d)
    elif t == "FetchArticleError":
        return FetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown type: %s" % (t,))
