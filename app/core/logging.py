import json
import logging
from contextvars import ContextVar

request_context: ContextVar[dict] = ContextVar("request_context", default={})
logger = logging.getLogger("meeting_assistant")


def log_event(event: str, **fields) -> None:
    logger.info(json.dumps({"event": event, **request_context.get(), **fields}, ensure_ascii=False, default=str))
