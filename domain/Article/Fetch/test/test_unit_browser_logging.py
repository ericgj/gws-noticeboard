import os
import random

# temporary
os.environ["APP_SUBDOMAIN"] = "Article"
os.environ["APP_SERVICE"] = "Fetch"
os.environ["APP_ENV"] = "test"
os.environ["APP_STATE"] = ""
os.environ["APP_PUBLISH_TOPIC"] = "article.fetch.events--test"
os.environ["APP_SUBSCRIBE_TOPIC"] = "article.core.events--test"

from shared.model.article import ArticleIssues
from main import _fetch_article
import env

from test.util.fetch import SAMPLE_URLS

logger = env.get_logger(__name__)


def fetch_one():
    root_logger = env.get_logger(None)
    assert root_logger.level > 0
    url = random.sample(SAMPLE_URLS, 1)[0]
    logger.info("Testing url: %s" % (url,), env.log_record(foo="bar"))
    try:
        article = _fetch_article(url)
        article.validate()

    except ArticleIssues as w:
        logger.warning(w, env.log_record(error=w.to_json(brief=True)))


# ------------------------------------------------------------------------------
# Note: run tests in a subprocess below to avoid pytest eating the logs
# ------------------------------------------------------------------------------

import subprocess
import json


def test_fetch_one():
    _run_in_subprocess("fetch_one", verify_has_at_least_n_logs(1))


def verify_has_at_least_n_logs(n):
    def _verify(logs, _):
        assert len(logs) >= n, "Expected at least %d log record, %d found" % (
            n,
            len(logs),
        )

    return _verify


def _run_in_subprocess(test_name, *verifiers):
    def _verify(lines, outp):
        for line in lines:
            print(line)
        assert len(lines) > 0, "Expected stderr output but there was none"

        logs = []
        for line in lines:
            if line.startswith("{"):
                log = json.loads(line)
                logs.append(log)
        for log in logs:
            print(json.dumps(log, indent=2))
        for verifier in verifiers:
            verifier(logs, outp)

    module_name = __name__
    py = "import {module_name}; getattr({module_name},'{test_name}')()".format(
        **locals()
    )
    p = subprocess.run(
        ["python", "-c", py], check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )

    lines = p.stderr.decode("utf8").strip().splitlines()
    outp = p.stdout.decode("utf8").strip()
    _verify(lines, outp)
