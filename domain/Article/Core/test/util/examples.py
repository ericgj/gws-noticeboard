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
        max_size=max_size
    )

def url_alpha_text(min_size=1, max_size=None):
    return hyp_extra.text(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        min_size=min_size,
        max_size=max_size
    )


def requested_article_examples(urls=None):
    return hyp.fixed_dictionaries(
        {"$type": hyp.just("RequestedArticle"), "url": url_examples(urls)}
    )
