from time import time, sleep
from urllib.parse import urlparse

import pytest

import browser
from config import Config, BodyParser
# from test.util.fetch import SAMPLE_URLS

SAMPLE_URLS = [
    "https://www.washingtonpost.com/education/2019/08/28/historians-slavery-myths/",
    "https://www.washingtonpost.com/lifestyle/2019/08/09/caught-between-young-kids-parent-with-alzheimers-i-found-lifeline-playground/",
]

"""
This works for the sample size of 2 ;) but as it seems fragile, currently
using the Newspaper parser.
"""
WASHPOST_TEST_CONFIGS = [
    Config(
        body_parser=BodyParser.BeautifulSoup,
        body_parser_options={
            "html_parsers": ["lxml", "html.parser", "html5lib"],
            "css_selectors": [".main", ".article-body"],
        },
    )
]

CONFIGS_0 = [Config()]
CONFIGS_1 = WASHPOST_TEST_CONFIGS


@pytest.mark.skip(reason="temporary")
def test_compare():
    results = {url: [[None, None, None], [None, None, None]] for url in SAMPLE_URLS}
    tries = 0
    for url in SAMPLE_URLS:
        tries = tries + 1
        if tries > 1:
            sleep(5)

        try:
            tstart0 = time()
            art0 = browser.fetch(url, CONFIGS_0)
            tend0 = time()
            results[url][0][0] = art0.text
            results[url][0][1] = len(art0.html)
            results[url][0][2] = tend0 - tstart0
        except Exception as e:
            results[url][0][0] = e
            continue

        sleep(5)

        try:
            tstart1 = time()
            art1 = browser.fetch(url, CONFIGS_1)
            tend1 = time()
            results[url][1][0] = art1.text
            results[url][1][1] = len(art1.html)
            results[url][1][2] = tend1 - tstart1
        except Exception as e:
            results[url][1][0] = e
            continue

    for (k, v) in results.items():
        netloc = urlparse(k).netloc
        r0, r1 = v
        print(
            "%s\n    0: %s | %s | %s\n    1: %s | %s | %s"
            % (
                netloc.ljust(22)[:20],
                "-" if r0[2] is None else str(r0[2]),
                "-" if r0[1] is None else str(r0[1]),
                str(r0[0]).replace("\n", " ").ljust(42)[:40],
                "-" if r1[2] is None else str(r1[2]),
                "-" if r1[1] is None else str(r1[1]),
                str(r1[0])
            )
        )

    errs = [
        v
        for v in results.values()
        if isinstance(v[0][0], Exception) or isinstance(v[1][0], Exception)
    ]

    if len(errs) > 0:
        raise ValueError("%d errors fetching" % (len(errs),))
