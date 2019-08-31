from dataclasses import dataclass, field
from enum import Enum


class Downloader(Enum):
    Newspaper = 1


class MetadataParser(Enum):
    Newspaper = 1


class BodyParser(Enum):
    Newspaper = 1
    BeautifulSoup = 2
    LXML = 3


@dataclass
class Config:
    downloader: Downloader = Downloader.Newspaper
    downloader_options: dict = field(default_factory=dict)
    metadata_parser: MetadataParser = MetadataParser.Newspaper
    metadata_parser_options: dict = field(default_factory=dict)
    body_parser: BodyParser = BodyParser.Newspaper
    body_parser_options: dict = field(default_factory=dict)
