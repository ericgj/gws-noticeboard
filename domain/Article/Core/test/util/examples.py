from datetime import timedelta

import hypothesis.strategies as hyp
import shared.util.hypothesis as hyp_extra


def url_examples(urls=None):
    if urls is None:
        return generated_url_examples()
    else:
        return hyp.sampled_from(urls)


def generated_url_examples():
    def _gen(parts):
        return "".join(
            [
                "https://",
                ".".join([p for p in parts[:-1] if p is not None]),
                "/",
                parts[-1],
            ]
        )

    return hyp.tuples(
        (hyp.none() | url_text()),
        url_text(),
        url_alpha_text(min_size=2, max_size=4),
        hyp.lists(url_text()).map(lambda parts: "/".join(parts)),
    ).map(_gen)


def url_text(min_size=1, max_size=None):
    return hyp_extra.text(
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_",
        min_size=min_size,
        max_size=max_size,
    )


def url_alpha_text(min_size=1, max_size=None):
    return hyp_extra.text(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        min_size=min_size,
        max_size=max_size,
    )


def requested_article_examples(urls=None):
    return hyp.fixed_dictionaries(
        {"$type": hyp.just("RequestedArticle"), "url": url_examples(urls)}
    )


def fetched_article_examples(dates_near=None, dates_range=(7, 7), size=1500):
    if dates_near is None:
        date_gen = hyp.none()
    else:
        min_value = dates_near - timedelta(days=dates_range[0])
        max_value = dates_near + timedelta(days=dates_range[1])
        date_gen = hyp.dates(min_value=min_value, max_value=max_value).map(
            lambda d: d.strftime("%Y-%m-%d")
        )

    return hyp.fixed_dictionaries(
        {
            "$type": hyp.just("FetchedArticle"),
            "title": hyp.text(),
            "authors": hyp.lists(hyp.text()),
            "encoding": hyp.just("utf8"),
            "raw_html": hyp.text(),
            "text": hyp.text(),
            "html": hyp.text(min_size=size, max_size=size),
            "publish_date": date_gen,
            "summary": hyp.none() | hyp.text(),
            "site_name": hyp.none() | hyp.text(),
        }
    )


def fetch_article_error_examples():
    return hyp.fixed_dictionaries(
        {
            "$type": hyp.just("FetchArticleError"),
            "error_type": hyp.text(),
            "error_message": hyp.text(),
        }
    )
