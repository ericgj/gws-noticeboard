from time import sleep
from typing import Iterator
from urllib.parse import urlparse

from html2text import HTML2Text
from markdown2 import markdown

from shared.adapter.logging import RetryException
from shared.model.article import FetchedArticle
from config import Config, Downloader, MetadataParser, BodyParser
import env
import strategy
import strategy.newspaper
import strategy.bs
import strategy.lxml

logger = env.get_logger(__name__)

CONFIG_MAP = {
    "nytimes.com": [
        Config(
            body_parser=BodyParser.BeautifulSoup,
            body_parser_options={
                "html_parsers": ["lxml", "html.parser", "html5lib"],
                "css_selectors": ["article .meteredContent"],
            },
        )
    ]
}


class FetchError(RetryException):
    pass


def configs_for_url(url: str) -> Iterator[Config]:
    _, key = url_site_and_domain(url)
    return CONFIG_MAP.get(key, [Config()])


def fetch(url: str, configs: Iterator[Config], pause=2) -> FetchedArticle:
    def _fetch():
        tries = 0
        for config in configs:
            tries = tries + 1
            html = None
            article = None
            body = None
            download_ctx = download_context(url, config.downloader)
            meta_ctx = metadata_parse_context(url, config.metadata_parser)
            body_ctx = body_parse_context(url, config.body_parser)

            if tries > 1:  # pause before trying another download
                sleep(pause)

            try:
                with env.log_elapsed(
                    "Downloading from {url_site} with {downloader}",
                    logger,
                    context=download_ctx,
                    raise_error=True,
                ):
                    html = get_downloader(config)(url)
            except Exception:
                continue

            try:
                with env.log_elapsed(
                    "Metadata parsing from {url_site} with {metadata_parser}",
                    logger,
                    context=meta_ctx,
                    raise_error=True,
                ):
                    article = get_metadata_parser(config)(url, html)
            except Exception:
                continue

            try:
                with env.log_elapsed(
                    "Article body parsing from {url_site} with {body_parser}",
                    logger,
                    context=body_ctx,
                    raise_error=True,
                ):
                    body = get_body_parser(config)(url, html, article)
            except Exception:
                continue

            article.text = markdown_from_html(body)
            article.html = markdown(article.text)
            yield article

    try:
        return next(_fetch())
    except StopIteration:
        raise FetchError("All %d fetch strategies failed for %s" % (len(configs), url))


def get_downloader(config: Config) -> strategy.Downloader:
    if config.downloader == Downloader.Newspaper:
        return strategy.newspaper.Downloader(config.downloader_options)
    else:
        raise ValueError("Unknown downloader: %s" % (config.downloader,))


def get_metadata_parser(config: Config) -> strategy.MetadataParser:
    if config.metadata_parser == MetadataParser.Newspaper:
        return strategy.newspaper.MetadataParser(config.metadata_parser_options)
    else:
        raise ValueError("Unknown metadata parser: %s" % (config.metadata_parser,))


def get_body_parser(config: Config) -> strategy.BodyParser:
    if config.body_parser == BodyParser.Newspaper:
        return strategy.newspaper.BodyParser(config.body_parser_options)
    elif config.body_parser == BodyParser.BeautifulSoup:
        return strategy.bs.BodyParser(config.body_parser_options)
    elif config.body_parser == BodyParser.LXML:
        return strategy.lxml.BodyParser(config.body_parser_options)
    else:
        raise ValueError("Unknown body parser: %s" % (config.body_parser,))


def download_context(url, downloader):
    site, domain = url_site_and_domain(url)
    return {
        "url": url,
        "url_site": site,
        "url_domain": domain,
        "downloader": str(downloader),
    }


def metadata_parse_context(url, metadata_parser):
    site, domain = url_site_and_domain(url)
    return {
        "url": url,
        "url_site": site,
        "url_domain": domain,
        "metadata_parser": str(metadata_parser),
    }


def body_parse_context(url, body_parser):
    site, domain = url_site_and_domain(url)
    return {
        "url": url,
        "url_site": site,
        "url_domain": domain,
        "body_parser": str(body_parser),
    }


def url_site_and_domain(url):
    _, site, _, _, _, _ = urlparse(url)
    return (site, ".".join(site.split(".")[-2:]))


def markdown_from_html(html):
    md_maker = HTML2Text()
    md_maker.escape_snob = True
    md_maker.inline_links = False
    return md_maker.handle(html)
