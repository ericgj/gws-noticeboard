from datetime import date
from typing import List, Optional
from dataclasses import dataclass

import shared.util.date_ as date_


@dataclass
class Article:
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
    def from_json(cls, d: dict) -> "Article":
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

    def to_json(self) -> dict:
        return {
            "$type": self.__class__.__name__,
            "site_name": self.site_name,
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "encoding": self.encoding,
            "raw_html": self.raw_html,
            "text": self.text,
            "html": self.html,
            "publish_date": (
                None if self.publish_date is None else date_.encode(self.publish_date)
            ),
        }

    def first_author(self) -> Optional[str]:
        return None if len(self.authors) == 0 else self.authors[0]
