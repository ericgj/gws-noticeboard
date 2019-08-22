from datetime import date
from typing import List, Optional
from dataclasses import dataclass

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
