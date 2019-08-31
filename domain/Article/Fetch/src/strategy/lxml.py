from lxml.cssselect import CSSSelector
import lxml.etree

from shared.model.article import Article
import strategy

"""
XML parser: note do not use this strategy unless you know for sure the
article is valid XML.
"""


class BodyParser(strategy.BodyParser):
    def __init__(self, options: dict = {}):
        self.css_selectors = options.get("css_selectors", [])
        self.xpath_selectors = options.get("xpath_selectors", [])
        if len(self.css_selectors) == 0 and len(self.xpath_selectors) == 0:
            raise ValueError("Expected either css_selectors or xpath_selectors options")
        super(BodyParser, self).__init__(options)

    def __call__(self, url: str, html: str, article: Article) -> str:
        def _select(el):
            for xpath in self.xpath_selectors:
                rs = el.xpath(xpath)
                if len(rs) == 0:
                    continue
                yield rs[0]

            for css in self.css_selectors:
                sel = CSSSelector(css)
                rs = sel(el)
                if len(rs) == 0:
                    continue
                yield rs[0]

        try:
            el = next(_select(lxml.etree.fromstring(html)))
        except StopIteration:
            raise strategy.ParseBodyError("Article body not found")

        return lxml.etree.tostring(el).decode(article.encoding)
