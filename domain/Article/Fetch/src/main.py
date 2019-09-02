from shared.adapter.pubsub import gcf_adapter
from shared.event.fetch import (
    FetchedArticle,
    FetchedArticleWithIssues,
    FailedFetchingArticle,
)
from shared.adapter.logging import RetryException
import shared.event.core as core_event
from shared.model.article import Article, ArticleIssues

import browser
import env

env.init_logging()
logger = env.get_logger(__name__)


def _fetch(event: core_event.Event, metadata: dict, ctx) -> str:
    if isinstance(event, core_event.SavedNewLink):
        try:
            article = _fetch_article(event.url)
            article.validate()
            env.publish(
                FetchedArticle(id=event.id, url=event.url, article=article).to_json()
            )

        except ArticleIssues as w:
            env.publish(
                FetchedArticleWithIssues(
                    id=event.id, url=event.url, issues=w.issues, article=w.article
                ).to_json()
            )
            raise

        except (Exception, RetryException) as e:
            env.publish(
                FailedFetchingArticle(id=event.id, url=event.url, error=e).to_json()
            )
            raise

        return done()  # Handled without error

    return done()  # Unhandled event


def _fetch_article(url: str) -> Article:
    configs = browser.configs_for_url(url)
    return browser.fetch(url, configs)


def done(x=None, returning=""):
    return returning


# ------------------------------------------------------------------------------
# CLOUD FUNCTION ENTRY POINTS
# ------------------------------------------------------------------------------

handle_errors = env.log_errors(logger, on_error=done, on_warning=done)
message_adapter = gcf_adapter(core_event.from_json)

fetch = handle_errors(message_adapter(_fetch))
