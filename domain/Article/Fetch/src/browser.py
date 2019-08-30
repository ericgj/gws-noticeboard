from typing import Optional

import newspaper
import lxml
from html2text import html2text
from markdown2 import markdown

from shared.model.article import Article

NP_GOOGLEBOT_CONFIG = {
    "browser_user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "headers": {"Referer": "https://www.google.com/"},
    "follow_meta_refresh": True,
}


def fetch(url: str) -> Article:
    """
    Note: a more sophisticated algorithm could examine the url and tweak 
    config based on it. The np_article could be evaluated to determine if 
    another scraping technique could work better.
    """
    np_article = fetch_np(url)
    article = parse_np(np_article)
    return article


def fetch_np(url: str, config: dict = {}) -> newspaper.Article:
    np_article = newspaper.Article(url, **config)
    np_article.download()
    np_article.parse()
    return np_article


def parse_np(np_article: newspaper.Article) -> Article:
    return Article(
        site_name=parse_np_site_name(np_article.meta_data),
        title=np_article.title,
        authors=np_article.authors,
        summary=parse_np_summary(np_article.meta_data),
        text=np_article.text,
        html=parse_np_html(np_article),
        publish_date=(
            None if np_article.publish_date is None else np_article.publish_date.date()
        ),
    )


def parse_np_html(np_article: newspaper.Article) -> str:
    raw_html = html_from_lxml(np_article.clean_top_node)
    try:
        return clean_html(raw_html, np_article.text)
    except Exception:
        return raw_html


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


def html_from_lxml(node: lxml.etree.ElementTree) -> str:
    return lxml.etree.tostring(node).decode("utf8")


# ------------------------------------------------------------------------------
# HTML cleaning via Markdown
# ------------------------------------------------------------------------------


def clean_html(html: str, text: Optional[str] = None) -> str:
    try:
        return cleaned_html(html)
    except Exception:
        return text_html(text)


def cleaned_html(html: str) -> str:
    return markdown(html2text(html))


def text_html(text: str) -> str:
    return markdown(text)
