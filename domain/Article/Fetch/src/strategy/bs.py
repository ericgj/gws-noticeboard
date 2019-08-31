import logging
from bs4 import BeautifulSoup

from shared.model.article import Article
import strategy

logger = logging.getLogger(__name__)


class ParseError(Exception):
    def __init__(self, parser, css, error):
        self.parser = parser
        self.css = css
        self.error = error

    def __str__(self):
        return "BeautifulSoup error using parser %s selecting '%s': %s" % (
            self.parser,
            self.css,
            str(self.error),
        )


class BodyParser(strategy.BodyParser):
    def __init__(self, options: dict = {}):
        self.html_parsers = options.get("html_parsers", ["html.parser"])
        self.css_selectors = options.get("css_selectors", [])
        if len(self.html_parsers) == 0:
            raise ValueError("Expected one or more html_parsers to be specified")
        if len(self.css_selectors) == 0:
            raise ValueError("Expected one or more css_selectors to be specified")
        super(BodyParser, self).__init__(options)

    def __call__(self, url: str, html: str, article: Article) -> str:
        def _select():
            for html_parser in self.html_parsers:
                for css in self.css_selectors:
                    try:
                        el = BeautifulSoup(html, html_parser)
                        rs = el.select(css)
                        if len(rs) == 0:
                            continue
                        yield rs[0]
                    except Exception as e:
                        logger.warning(
                            "Note parsing failed: %s"
                            % (ParseError(parser=html_parser, css=css, error=e),)
                        )
                        continue

        try:
            el = next(_select())
        except StopIteration:
            raise strategy.ParseBodyError("Article body not found")

        return str(el)
