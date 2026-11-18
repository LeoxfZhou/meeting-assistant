"""Small OpenAI-compatible JSON generation client; no SDK/provider framework."""
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable
import httpx
from pydantic import BaseModel, ValidationError
from app.core.config import Settings
from app.core.logging import log_event


class LLMError(Exception):
    def __init__(self, kind: str, status_code: int = 502):
        self.kind = kind
        self.status_code = status_code
        super().__init__(kind)


class LLMClient:
    def __init__(self, settings: Settings, *, transport=None, sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self.transport = transport
        self.sleep = sleep

    def generate(self, messages: list[dict[str, str]], schema: type[BaseModel]) -> BaseModel:
        s = self.settings
        if not (s.llm_api_key.get_secret_value() and s.llm_base_url and s.llm_model):
            raise LLMError("provider_not_configured", 503)
        if not s.llm_base_url.startswith("https://"):
            raise LLMError("provider_requires_https", 503)
        start = time.monotonic()
        attempts = max(1, min(s.llm_max_attempts, 4))
        with httpx.Client(timeout=httpx.Timeout(s.llm_read_timeout, connect=s.llm_connect_timeout),
                          transport=self.transport, follow_redirects=False) as client:
            for attempt in range(attempts):
                error = None
                retry_after = None
                try:
                    response = client.post(s.llm_base_url.rstrip('/') + '/chat/completions',
                        headers={"Authorization": "Bearer " + s.llm_api_key.get_secret_value()},
                        json={"model": s.llm_model, "messages": messages, "temperature": 0,
                              "max_tokens": 4096, "response_format": {"type": "json_object"}})
                    if response.status_code in {401, 403}:
                        raise LLMError("provider_unauthorized", 502)
                    if response.status_code == 429 or response.status_code >= 500:
                        error = "rate_limited" if response.status_code == 429 else "provider_server_error"
                        retry_after = response.headers.get("Retry-After")
                    elif response.status_code != 200:
                        raise LLMError("provider_request_rejected")
                    else:
                        try:
                            body = response.json()
                            choice = body["choices"][0]
                            if choice.get("finish_reason") != "stop":
                                raise LLMError("incomplete_generation")
                            parsed = schema.model_validate_json(choice["message"]["content"])
                        except (ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
                            raise LLMError("invalid_structured_output") from exc
                        usage = body.get("usage") or {}
                        # 只接纳非负整数，不把供应商原始响应或 Key 写入日志。
                        safe_usage = {k: v for k, v in usage.items() if k in
                                      {"prompt_tokens", "completion_tokens", "total_tokens"}
                                      and type(v) is int and v >= 0} if isinstance(usage, dict) else {}
                        log_event("llm", model=s.llm_model, latency_ms=round((time.monotonic()-start)*1000),
                                  status="success", token_usage=safe_usage, estimated_cost=None, attempts=attempt+1)
                        return parsed
                except httpx.ConnectTimeout:
                    error = "connect_timeout"
                except httpx.ReadTimeout:
                    error = "read_timeout"
                except httpx.TimeoutException:
                    error = "timeout"
                except httpx.TransportError:
                    error = "transport_error"
                if attempt + 1 == attempts:
                    log_event("llm", model=s.llm_model, latency_ms=round((time.monotonic()-start)*1000),
                              status="failed", error_type=error, attempts=attempt+1)
                    raise LLMError(error or "provider_error", 504 if error and 'timeout' in error else 502)
                delay = min(2 ** attempt, 8)
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        try:
                            delay = max(delay, (parsedate_to_datetime(retry_after)-datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError, OverflowError):
                            delay = max(delay, 0)
                self.sleep(min(max(delay, 0), 10))
        raise LLMError("provider_error")
