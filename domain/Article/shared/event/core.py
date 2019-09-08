from dataclasses import dataclass
from typing import Union


@dataclass
class SavedArticle:
    id: str
    url: str

    @classmethod
    def from_json(cls, d: dict):
        return cls(id=d["id"], url=d["url"])

    def to_json(self) -> dict:
        return {"$type": self.__class__.__name__, "id": self.id, "url": self.url}

    def __str__(self):
        return '%s(id="%s", url="%s")' % (self.__class__.__name__, self.id, self.url)


class SavedNewRequestedArticle(SavedArticle):
    pass


class SavedFetchedArticle(SavedArticle):
    pass


class SavedFetchArticleError(SavedArticle):
    pass


Event = Union[SavedNewRequestedArticle, SavedFetchedArticle, SavedFetchArticleError]


def from_json(d: dict) -> Event:
    t = d.get("$type", None)
    if t == "SavedNewRequestedArticle":
        return SavedNewRequestedArticle.from_json(d)
    elif t == "SavedFetchedArticle":
        return SavedFetchedArticle.from_json(d)
    elif t == "SavedFetchArticleError":
        return SavedFetchArticleError.from_json(d)
    else:
        raise ValueError("Unknown event: %s" % (t,))
