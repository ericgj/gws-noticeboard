from shared.adapter.pubsub import gcf_adapter
from shared.event.fetch import (
    FetchedArticle,
    FetchedArticleWithIssues,
    FailedFetchingArticle,
)
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
            logger.warning(w, env.log_record(error=w.to_json()))
            env.publish(
                FetchedArticleWithIssues(
                    id=event.id, url=event.url, issues=w.issues, article=w.article
                ).to_json()
            )

        except Exception as e:
            env.publish(
                FailedFetchingArticle(id=event.id, url=event.url, error=e).to_json()
            )
            raise e from None

    return ""


def _fetch_article(url: str) -> Article:
    configs = browser.configs_for_url(url)
    return browser.fetch(url, configs)


# ------------------------------------------------------------------------------
# CLOUD FUNCTION ENTRY POINTS
# ------------------------------------------------------------------------------

fetch = env.log_errors(logger)(gcf_adapter(core_event.from_json)(_fetch))
