import newspaper
import lxml
from html2text import html2text
from markdown2 import markdown

from model.article import Article, Request

NP_GOOGLEBOT_CONFIG = {
    "browser_user_agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "headers": {"Referer": "https://www.google.com/"},
    "follow_meta_refresh": True,
}


def fetch(request: Request):
    """
    Note: a more sophisticated algorithm could examine the url and tweak 
    config based on it. The np_article could be evaluated to determine if 
    another scraping technique could work better.
    """
    np_article = fetch_np(request.url, config=NP_GOOGLEBOT_CONFIG)
    article = parse_np(np_article, note=request.note)
    return article


def fetch_np(url, config={}):
    np_article = newspaper.Article(url, **config)
    np_article.download()
    np_article.parse()
    return np_article


def parse_np(np_article, note=None):
    return Article(
        url=np_article.url if np_article.canonical_link is None else np_article.url,
        note=note,
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


def parse_np_html(np_article):
    raw_html = html_from_lxml(np_article.clean_top_node)
    try:
        return clean_html(raw_html, np_article.text)
    except Exception:
        return raw_html


def parse_np_site_name(meta):
    if "og" in meta:
        return parse_np_site_name_og(meta["og"])
    if "shareaholic" in meta:
        return parse_np_site_name_shareaholic(meta["shareaholic"])
    return None


def parse_np_site_name_og(og):
    return og.get("site_name", None)


def parse_np_site_name_shareaholic(sh):
    return sh.get("site_name", None)


def parse_np_summary(meta):
    if "og" in meta:
        return parse_np_summary_og(meta["og"])
    return meta.get("description", None)


def parse_np_summary_og(og):
    return og.get("description", None)


def html_from_lxml(node):
    return lxml.etree.tostring(node).decode("utf8")


# ------------------------------------------------------------------------------
# HTML cleaning via Markdown
# ------------------------------------------------------------------------------


def clean_html(html, text=None):
    try:
        return cleaned_html(html)
    except Exception:
        return text_html(text)


def cleaned_html(html):
    return markdown(html2text(html))


def text_html(text):
    return markdown(text)
