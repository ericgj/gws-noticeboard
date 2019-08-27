from dataclasses import dataclass
from typing import Union


@dataclass
class FetchArticle:
    url: str

    @classmethod
    def from_json(cls, d: dict) -> "FetchArticle":
        return cls(url=d["url"])

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "url": self.url}

    @property
    def id(self) -> str:
        return self.url


Command = Union[FetchArticle]


def from_json(d: dict) -> Command:
    t = d.get("$type", None)
    if t == "FetchArticle":
        return FetchArticle.from_json(d)
    else:
        raise ValueError("Unknown command: %s" % (t,))
