import os
import random
from time import sleep

# import pytest

from shared.model.article import ArticleIssues
from main import _fetch_article
import env

from test.util.fetch import SAMPLE_URLS

logger = env.get_logger(__name__)


def fetch_one():
    root_logger = env.get_logger(None)
    assert root_logger.level > 0

    assert os.environ.get("APP_SUBDOMAIN") is not None

    url = random.sample(SAMPLE_URLS, 1)[0]
    logger.info("Testing url: {url} in service {app_service}", env.log_record(url=url))
    try:
        article = _fetch_article(url)
        article.validate()

    except ArticleIssues as w:
        logger.warning(w, env.log_record(**w.to_json()))


def logging_elapsed():
    with env.log_elapsed(
        "Testing log_elapsed, expecting 1 sec but was {seconds} sec",
        logger,
        context={"log_type": "TestingLogElapsed"}
    ):
        sleep(1)

# ------------------------------------------------------------------------------
# Note: run tests in a subprocess below to avoid pytest eating the logs
# ------------------------------------------------------------------------------

import subprocess
import json


# @pytest.mark.skip(reason="temporary")
def test_fetch_one():
    _run_in_subprocess(
        "fetch_one",
        verify_has_at_least_n_logs(1),
        verify_each_log_has_log_fields,
        verify_each_log_has_app_fields,
        verify_each_log_message_is_resolved,
        # force_fail
    )

def test_logging_elapsed():
    _run_in_subprocess(
        "logging_elapsed",
        verify_has_at_least_n_logs(1),
        verify_has_time_elapsed_fields(0),
        verify_has_log_type(0, "TestingLogElapsed")
    )


"""
def force_fail(n, _):
    assert False
"""


def verify_has_at_least_n_logs(n):
    def _verify(logs, _):
        assert len(logs) >= n, "Expected at least %d log record, %d found" % (
            n,
            len(logs),
        )

    return _verify


def verify_each_log_has_log_fields(logs, _):
    for log in logs:
        keys = log.keys()
        assert "log_name" in keys, 'Missing "log_name"'
        assert "log_level" in keys, 'Missing "log_level"'
        assert "log_levelno" in keys, 'Missing "log_levelno"'
        assert "log_asctime" in keys, 'Missing "log_asctime"'
        assert "log_created" in keys, 'Missing "log_created"'
        assert "log_pathname" in keys, 'Missing "log_pathname"'
        assert "log_module" in keys, 'Missing "log_module"'
        assert "log_funcName" in keys, 'Missing "log_funcName"'
        assert "log_lineno" in keys, 'Missing "log_lineno"'
        assert "message" in keys, 'Missing "message"'


def verify_each_log_has_app_fields(logs, _):
    for log in logs:
        keys = log.keys()
        assert "app_subdomain" in keys, 'Missing "app_subdomain"'
        assert "app_service" in keys, 'Missing "app_service"'
        assert "app_environment" in keys, 'Missing "app_environment"'
        assert "app_state" in keys, 'Missing "app_state"'
        assert "app_publish_topic" in keys, 'Missing "app_publish_topic"'
        assert "app_subscribe_topic" in keys, 'Missing "app_subscribe_topic"'


def verify_each_log_message_is_resolved(logs, _):
    for log in logs:
        assert not "{" in log["message"], "Apparenly unresolved message: %s" % (
            log["message"],
        )

def verify_has_log_type(i, expected):
    def _verify(logs, _):
        log = logs[i]
        assert "log_type" in log, 'Missing "log_type"'
        assert log["log_type"] == expected
    return _verify

def verify_has_time_elapsed_fields(i):
    def _verify(logs, _):
        log = logs[i]
        keys = log.keys()
        assert "seconds" in keys, 'Missing "seconds"'
        assert "milliseconds" in keys, 'Missing "milliseconds"'
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
