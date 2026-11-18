import json
import logging
from contextvars import ContextVar

request_context: ContextVar[dict] = ContextVar("request_context", default={})
logger = logging.getLogger("meeting_assistant")


def log_event(event: str, **fields) -> None:
    logger.log(logging.ERROR if fields.get("status") == "failed" else logging.INFO, json.dumps({"event": event, "request_id": None, "user_id": None, "meeting_id": None, "model": None,
                            "latency_ms": None, "token_usage": None, "status": None, "error_type": None,
                            **request_context.get(), **fields}, ensure_ascii=False, default=str))
