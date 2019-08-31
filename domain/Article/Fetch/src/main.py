from shared.adapter.pubsub import gcf_adapter
from shared.event.fetch import FetchedArticle, FailedFetchingArticle
import shared.event.core as core_event
from shared.model.article import Article

import browser
import env


def _fetch(event: core_event.Event, metadata: dict, ctx) -> str:
    if isinstance(event, core_event.SavedNewLink):
        try:
            article = _fetch_article(event.url)
        except Exception as e:
            env.publish(
                FailedFetchingArticle(id=event.id, url=event.url, error=e).to_json()
            )
            raise e

        env.publish(
            FetchedArticle(id=event.id, url=event.url, article=article).to_json()
        )

    return ""


def _fetch_article(url: str) -> Article:
    configs = browser.configs_for_url(url)
    return browser.fetch(url, configs)


# ------------------------------------------------------------------------------
# CLOUD FUNCTION ENTRY POINTS
# ------------------------------------------------------------------------------

fetch = gcf_adapter(core_event.from_json)(_fetch)
