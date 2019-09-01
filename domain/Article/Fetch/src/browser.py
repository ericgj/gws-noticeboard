from time import sleep
from typing import Iterator
from urllib.parse import urlparse

from html2text import HTML2Text
from markdown2 import markdown

from shared.model.article import Article
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


class FetchError(Exception):
    pass


def configs_for_url(url: str) -> Iterator[Config]:
    _, netloc, _, _, _, _ = urlparse(url)
    key = ".".join(netloc.lower().split(".")[-2:])
    return CONFIG_MAP.get(key, [Config()])


def fetch(url: str, configs: Iterator[Config]) -> Article:
    def _fetch():
        tries = 0
        for config in configs:
            tries = tries + 1
            try:
                if tries > 1:  # pause before trying another download
                    sleep(2)
                logger.info(
                    "Trying download with %s" % (config.downloader,),
                    env.log_record(downloader=str(config.downloader)),
                )
                html = get_downloader(config)(url)
            except Exception as e:
                logger.warning(
                    "Download failed for %s: %s" % (config.downloader, e),
                    env.log_record(downloader=str(config.downloader), error=e),
                )
                continue

            try:
                logger.info(
                    "Trying metatdata parse with %s" % (config.metadata_parser,),
                    env.log_record(metadata_parser=str(config.metadata_parser)),
                )
                article = get_metadata_parser(config)(url, html)
            except Exception as e:
                logger.warning(
                    "Metadata parse failed for %s: %s" % (config.metadata_parser, e),
                    env.log_record(
                        metadata_parser=str(config.metadata_parser), error=e
                    ),
                )
                continue

            try:
                logger.info(
                    "Trying body parse with %s" % (config.body_parser,),
                    env.log_record(body_parser=str(config.body_parser)),
                )
                body = get_body_parser(config)(url, html, article)
            except Exception as e:
                logger.warning(
                    "Body parse failed for %s: %s" % (config.body_parser, e),
                    env.log_record(body_parser=str(config.body_parser), error=e),
                )
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


def markdown_from_html(html):
    md_maker = HTML2Text()
    md_maker.escape_snob = True
    md_maker.inline_links = False
    return md_maker.handle(html)
