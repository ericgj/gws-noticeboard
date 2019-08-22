from urllib.parse import urlparse

from adapter import browser
from model.article import Request
from test.util.fetch import SAMPLE_URLS


def test_fetch_config_compare():
    results = {url: [None, None] for url in SAMPLE_URLS}
    for url in SAMPLE_URLS:
        try:
            req = Request(url=url, note=None)
            art0 = browser.parse_np(browser.fetch_np(req.url), req.note)
            results[url][0] = art0.text
        except Exception as e:
            results[url][0] = e
            continue

    for url in SAMPLE_URLS:
        try:
            req = Request(url=url, note=None)
            art1 = browser.parse_np(
                browser.fetch_np(req.url, config=browser.NP_GOOGLEBOT_CONFIG), req.note
            )
            results[url][1] = art1.text
        except Exception as e:
            results[url][1] = e
            continue

    for (k, v) in results.items():
        netloc = urlparse(k).netloc
        r0, r1 = v
        print(
            "%s | %s | %s"
            % (
                netloc.ljust(22)[:20],
                str(r0).replace("\n", " ").ljust(42)[:40],
                str(r1).replace("\n", " ").ljust(42)[:40],
            )
        )

    errs = [
        v
        for v in results.values()
        if isinstance(v[0], Exception) or isinstance(v[1], Exception)
    ]

    if len(errs) > 0:
        raise ValueError("%d errors fetching" % (len(errs),))
