from shared.adapter import logging
from shared.adapter import pubsub
from shared.event.fetch import (
    SucceededFetchingArticle,
    SucceededFetchingArticleWithIssues,
    FailedFetchingArticle,
)
import shared.event.core as core_event
from shared.model.article import FetchedArticle, ArticleIssues

import browser
import env

env.init_logging()
logger = env.get_logger(__name__)


def _fetch(event: core_event.Event, metadata: dict, ctx) -> str:
    if isinstance(event, core_event.SavedNewRequestedArticle):
        try:
            article = _fetch_article(event.url)
            article.validate()
            env.publish(
                SucceededFetchingArticle(
                    id=event.id, url=event.url, article=article
                ).to_json()
            )

        except ArticleIssues as w:
            env.publish(
                SucceededFetchingArticleWithIssues(
                    id=event.id, url=event.url, issues=w.issues, article=w.article
                ).to_json()
            )
            raise

        except (Exception, logging.RetryException) as e:
            env.publish(
                FailedFetchingArticle(id=event.id, url=event.url, error=e).to_json()
            )
            raise

        return done()  # Handled without error

    return done()  # Unhandled event


def _fetch_article(url: str) -> FetchedArticle:
    configs = browser.configs_for_url(url)
    return browser.fetch(url, configs)


def done(x=None, returning=""):
    return returning


# ------------------------------------------------------------------------------
# CLOUD FUNCTION ENTRY POINTS
# ------------------------------------------------------------------------------

handle_errors = logging.log_errors(logger, on_error=done, on_warning=done)
message_adapter = pubsub.gcf_adapter(core_event.from_json)

fetch = handle_errors(message_adapter(_fetch))
