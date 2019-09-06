from shared.adapter import pubsub
from shared.adapter import logging
from shared.command import UnknownCommandError
from shared.command import core as core_command
from shared.event import core as core_event
from shared.event import fetch as fetch_event
from shared.model.article import RequestedArticle
from shared.util.url import standardized_url

import adapter.storage as storage

import env


def done(x=None, returning=""):
    return returning


env.init_logging()
logger = env.get_logger(__name__)

# ------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------


def _core(command: core_command.Command, attributes: dict, ctx) -> str:
    logger.info("Received command {command}", env.log_record(command=command.to_json()))
    if isinstance(command, core_command.RequestArticle):
        url = standardized_url(command.url)
        request = RequestedArticle(url=url)
        id, is_new = storage.store_requested_article(
            env.storage_client(), request=request, note=command.note
        )
        if is_new:
            env.publish(core_event.SavedNewRequestedArticle(id=id, url=url).to_json())
        return done()

    raise UnknownCommandError(command)


def _from_fetch(event: fetch_event.Event, attributes: dict, ctx) -> str:
    raise NotImplementedError()


# ------------------------------------------------------------------------------
# CLOUD FUNCTION ENTRY POINTS
# ------------------------------------------------------------------------------

handle_errors = logging.log_errors(logger, on_error=done, on_warning=done)
command_adapter = pubsub.gcf_adapter(core_command.from_json)
fetch_event_adapter = pubsub.gcf_adapter(fetch_event.from_json)

core = handle_errors(command_adapter(_core))
from_fetch = handle_errors(fetch_event_adapter(_from_fetch))
