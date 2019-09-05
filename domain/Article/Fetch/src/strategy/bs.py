from bs4 import BeautifulSoup

from shared.model.article import FetchedArticle
import env
import strategy

logger = env.get_logger(__name__)


class BodyParser(strategy.BodyParser):
    def __init__(self, options: dict = {}):
        self.html_parsers = options.get("html_parsers", ["lxml"])
        self.css_selectors = options.get("css_selectors", [])
        if len(self.html_parsers) == 0:
            raise ValueError("Expected one or more html_parsers to be specified")
        if len(self.css_selectors) == 0:
            raise ValueError("Expected one or more css_selectors to be specified")
        super(BodyParser, self).__init__(options)

    def __call__(self, url: str, html: str, article: FetchedArticle) -> str:
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
                            "BeautifulSoup error using parser {html_parser}"
                            "selecting '{css_selector}': {error}",
                            env.log_record(
                                log_type="BeautifulSoupError",
                                html_parser=html_parser,
                                css_selector=css,
                                error=e,
                            ),
                        )
                        continue

        try:
            el = next(_select())
        except StopIteration:
            raise strategy.ParseBodyError("Article body not found")

        return str(el)
