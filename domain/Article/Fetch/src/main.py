from shared.adapter.pubsub import gcf_adapter
from shared.model.fetch import command
from shared.model.core.command import SaveArticle, SaveFetchArticleError
from shared.model.article import Article

import browser
import env


@gcf_adapter(command.from_json)
def fetch(cmd: command.Command, ctx) -> str:
    try:
        article = fetch_article(cmd)
    except Exception as e:
        env.publish(SaveFetchArticleError(url=cmd.url, error=e).to_json())
        raise e
    env.publish(SaveArticle(url=cmd.url, article=article).to_json())

    return ""


def fetch_article(cmd: command.Command) -> Article:
    return browser.fetch(cmd)
