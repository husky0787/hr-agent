"""Bounded Responses API calls with GPT-first, process-local xAI failover."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass

import httpx

from shared.config import positive_int

logger = logging.getLogger(__name__)


class ChatError(Exception):
    def __init__(self, message: str, *, fallback: bool = False, category: str = "provider"):
        super().__init__(message)
        self.fallback = fallback
        self.category = category


@dataclass(frozen=True)
class Provider:
    name: str
    key: str
    base_url: str
    model: str
    actor: str = ""


def configured_provider(name: str) -> Provider:
    prefix = "OPENAI" if name == "gpt" else "XAI"
    return Provider(
        name,
        os.getenv(f"{prefix}_API_KEY", ""),
        (os.getenv(f"{prefix}_BASE_URL") or (
            "https://share.transmd.cloud/v1" if name == "gpt" else "https://api.x.ai/v1"
        )).rstrip("/"),
        os.getenv(f"{prefix}_MODEL") or ("gpt-6.1-sol" if name == "gpt" else "grok-4.3"),
        os.getenv("OPENAI_ACTOR_AUTHORIZATION", "") if name == "gpt" else "",
    )


class CircuitBreaker:
    def __init__(self):
        self._lock = threading.Lock()
        self.until = 0.0
        self.probing = False

    def claim(self) -> bool:
        with self._lock:
            if not self.until:
                return True
            if time.monotonic() < self.until or self.probing:
                return False
            self.probing = True
            return True

    def success(self) -> None:
        with self._lock:
            self.until = 0.0
            self.probing = False

    def failure(self) -> None:
        with self._lock:
            self.until = time.monotonic() + positive_int("CHAT_FALLBACK_COOLDOWN_SECONDS", 60)
            self.probing = False

    def release(self) -> None:
        with self._lock:
            self.probing = False


circuit = CircuitBreaker()


def _http_error(response: httpx.Response) -> ChatError:
    try:
        payload = response.json()
        error = payload.get("error", {})
        if not isinstance(error, dict):
            error = {}
        code = str(error.get("code", "")) + " " + str(error.get("type", ""))
        message = str(error.get("message", ""))
    except (ValueError, AttributeError):
        code, message = "", ""
    safety = any(word in (code + " " + message).lower() for word in (
        "content_policy", "content_filter", "safety", "moderation", "policy violation",
    ))
    status = response.status_code
    authorization = any(word in (code + " " + message).lower() for word in (
        "permission", "authentication", "invalid_api", "access_denied", "not_authorized", "unauthorized", "account",
    ))
    fallback = not safety and (status in (401, 404, 408, 429) or status >= 500 or (status == 403 and authorization))
    return ChatError(
        "這個要求暫時未能處理，請調整問題後再試。" if not fallback
        else "聊天服務暫時未能連接，請稍後再試。",
        fallback=fallback,
        category="safety" if safety else f"http_{status}",
    )


async def _request(provider: Provider, messages: list[dict]) -> str:
    if not provider.key:
        raise ChatError("聊天服務尚未設定 API Key。", fallback=True, category="missing_key")
    headers = {"Authorization": f"Bearer {provider.key}"}
    if provider.actor:
        headers["x-openai-actor-authorization"] = provider.actor
    timeout = positive_int("CHAT_TIMEOUT_SECONDS", 30)
    body = {
        "model": provider.model, "input": messages, "store": False,
        "max_output_tokens": positive_int("CHAT_MAX_OUTPUT_TOKENS", 1200),
    }
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=min(5, timeout)), follow_redirects=False,
        ) as client:
            response = await asyncio.wait_for(
                client.post(f"{provider.base_url}/responses", headers=headers, json=body), timeout,
            )
        if response.status_code >= 300:
            raise _http_error(response)
        try:
            payload = response.json()
            if payload.get("status") == "incomplete":
                raise ChatError("回覆未能完整產生，請縮短問題或稍後再試。", category="incomplete")
            output = payload.get("output", [])
            text = "".join(
                part.get("text", "") if part.get("type") == "output_text" else part.get("refusal", "")
                for item in output if isinstance(item, dict)
                for part in item.get("content", []) if isinstance(part, dict)
                if part.get("type") in ("output_text", "refusal")
            ).strip()
            if not text:
                raise ValueError("empty response")
        except (ValueError, TypeError, AttributeError):
            raise ChatError("聊天服務返回無效回覆。", fallback=True, category="invalid_response") from None
        usage = payload.get("usage", {})
        logger.info("chat provider=%s seconds=%.2f input_tokens=%s output_tokens=%s",
                    provider.name, time.monotonic() - started,
                    usage.get("input_tokens"), usage.get("output_tokens"))
        return text
    except (httpx.TransportError, asyncio.TimeoutError):
        raise ChatError("聊天服務連線逾時，請稍後再試。", fallback=True, category="connection") from None


async def answer(messages: list[dict]) -> tuple[str, str]:
    if circuit.claim():
        try:
            text = await _request(configured_provider("gpt"), messages)
        except asyncio.CancelledError:
            circuit.release()
            raise
        except ChatError as exc:
            if not exc.fallback:
                circuit.release()
                raise
            circuit.failure()
            logger.warning("chat fallback from=gpt reason=%s", exc.category)
        else:
            circuit.success()
            return text, "gpt"
    try:
        return await _request(configured_provider("xai"), messages), "xai"
    except ChatError as exc:
        logger.warning("chat failed provider=xai reason=%s", exc.category)
        raise
