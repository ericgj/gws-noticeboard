from shared.model.article import Article

"""
ABCs for strategy classes
"""


class Downloader:
    def __init__(self, options: dict = {}):
        self.options = options

    def __call__(self, url: str) -> str:
        raise NotImplementedError()


class MetadataParser:
    def __init__(self, options: dict = {}):
        self.options = options

    def __call__(self, url: str, html: str) -> Article:
        raise NotImplementedError()


class BodyParser:
    def __init__(self, options: dict = {}):
        self.options = options

    def __call__(self, url: str, html: str, article: Article) -> str:
        raise NotImplementedError()


class DownloadError(Exception):
    pass


class ParseMetadataError(Exception):
    pass


class ParseBodyError(Exception):
    pass
