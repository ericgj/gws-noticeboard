from datetime import date
from typing import List, Optional
from dataclasses import dataclass

import newspaper
import lxml
from html2text import html2text
from markdown2 import markdown

import util.date_ as date_


@dataclass
class Request:
    url: str
    note: str = None

    @classmethod
    def from_json(cls, d):
        return cls(url=d["url"], note=d.get("note", None))

    def to_json(self):
        return {"$type": self.__class__.__name__, "url": self.url, "note": self.note}


@dataclass
class Article:
    url: str
    title: str
    authors: List[str]
    text: str
    html: str
    publish_date: Optional[date] = None
    summary: Optional[str] = None
    site_name: Optional[str] = None
    note: Optional[str] = None

    @classmethod
    def fetch(cls, request: Request):
        article = newspaper.Article(request.url)
        article.download()
        return cls.from_fetched_article(article, note=request.note)

    @classmethod
    def from_fetched_article(
        cls, article: newspaper.Article, note: Optional[str] = None
    ):
        article.parse()
        return cls(
            url=article.url if article.canonical_link is None else article.url,
            note=note,
            site_name=parse_site_name(article.meta_data),
            title=article.title,
            authors=article.authors,
            summary=parse_summary(article.meta_data),
            text=article.text,
            html=parse_html(article),
            publish_date=(
                None if article.publish_date is None else article.publish_date.date()
            ),
        )

    @classmethod
    def from_json(cls, d):
        return cls(
            url=d["url"],
            note=d.get("note", None),
            site_name=d.get("site_name", None),
            title=d["title"],
            authors=list(d["authors"]),
            summary=d.get("summary", None),
            text=d["text"],
            html=d["html"],
            publish_date=(
                None
                if d.get("publish_date", None) is None
                else date_.decode(d["publish_date"])
            ),
        )

    def to_json(self):
        return {
            "$type": self.__class__.__name__,
            "url": self.url,
            "note": self.note,
            "site_name": self.site_name,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "text": self.text,
            "html": self.html,
            "publish_date": (
                None if self.publish_date is None else date_.encode(self.publish_date)
            ),
        }

    def first_author(self):
        return None if len(self.authors) == 0 else self.authors[0]


def parse_html(article):
    try:
        return cleaned_html(article)
    except Exception:
        try:
            return raw_html(article)
        except Exception:
            return text_html(article)


def cleaned_html(article):
    return markdown(html2text(raw_html(article)))


def raw_html(article):
    return lxml.etree.tostring(article.clean_top_node).decode("utf8")


def text_html(article):
    return markdown(article.text)


def parse_site_name(meta):
    if "og" in meta:
        return parse_site_name_og(meta["og"])
    if "shareaholic" in meta:
        return parse_site_name_shareaholic(meta["shareaholic"])
    return None


def parse_site_name_og(og):
    return og.get("site_name", None)


def parse_site_name_shareaholic(sh):
    return sh.get("site_name", None)


def parse_summary(meta):
    if "og" in meta:
        return parse_summary_og(meta["og"])
    return meta.get("description", None)


def parse_summary_og(og):
    return og.get("description", None)
