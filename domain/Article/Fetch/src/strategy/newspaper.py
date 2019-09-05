from typing import Optional

import lxml.etree
from bs4 import UnicodeDammit
import newspaper

from shared.model.article import FetchedArticle
import strategy

GOOGLEBOT_OPTIONS = {
    "browser_user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "headers": {"Referer": "https://www.google.com/"},
    "follow_meta_refresh": True,
}


class Downloader(strategy.Downloader):
    def __init__(self, options: dict = {}):
        if options.get("as_googlebot", False) is True:
            options2 = options.copy()
            options2.update(GOOGLEBOT_OPTIONS)
            super(Downloader, self).__init__(options2)
        else:
            super(Downloader, self).__init__(options)

    def __call__(self, url: str) -> str:
        article = newspaper.Article(url, **self.options)
        article.download()
        html = article.html
        if html is None or len(html) == 0:
            raise strategy.DownloadError("Nothing downloaded")
        return html


class MetadataParser(strategy.MetadataParser):
    def __call__(self, url: str, html: str) -> FetchedArticle:
        article = newspaper.Article(url, **self.options)
        article.set_html(html)
        article.parse()
        return parse_np(article)


class BodyParser(strategy.BodyParser):
    def __call__(self, url: str, html: str, article: FetchedArticle) -> str:
        if article.html is None:
            article = newspaper.Article(url, **self.options)
            article.download(input_html=html)
            article.parse()
            return parse_np_html(article)
        else:
            return article.html


def parse_np(np_article: newspaper.Article) -> FetchedArticle:
    encoding = parse_np_encoding(np_article)
    html = parse_np_html(np_article, encoding)
    return FetchedArticle(
        site_name=parse_np_site_name(np_article.meta_data),
        title=np_article.title,
        authors=np_article.authors,
        summary=parse_np_summary(np_article.meta_data),
        encoding=encoding,
        raw_html=html,
        text=np_article.text,
        html=html,
        publish_date=(
            None if np_article.publish_date is None else np_article.publish_date.date()
        ),
    )


def parse_np_encoding(np_article: newspaper.Article) -> str:
    attempt = UnicodeDammit(np_article.html).original_encoding
    return "utf8" if attempt is None else attempt


def parse_np_html(np_article: newspaper.Article, encoding=None) -> str:
    if encoding is None:
        encoding = parse_np_encoding(np_article)
    return html_from_lxml(np_article.clean_top_node, encoding)


def parse_np_site_name(meta: dict) -> Optional[str]:
    if "og" in meta:
        return parse_np_site_name_og(meta["og"])
    if "shareaholic" in meta:
        return parse_np_site_name_shareaholic(meta["shareaholic"])
    return None


def parse_np_site_name_og(og: dict) -> Optional[str]:
    return og.get("site_name", None)


def parse_np_site_name_shareaholic(sh: dict) -> Optional[str]:
    return sh.get("site_name", None)


def parse_np_summary(meta: dict) -> Optional[str]:
    if "og" in meta:
        return parse_np_summary_og(meta["og"])
    return meta.get("description", None)


def parse_np_summary_og(og: dict) -> Optional[str]:
    return og.get("description", None)


def html_from_lxml(node: lxml.etree.ElementTree, encoding) -> str:
    return lxml.etree.tostring(node).decode(encoding)
