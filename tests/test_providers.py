import asyncio
import json
import time

import httpx
import pytest

from agent import providers


def completion(text="answer", **extra):
    return {"status": "completed", "output": [{"content": [{"type": "output_text", "text": text}]}], **extra}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "primary-secret")
    monkeypatch.setenv("XAI_API_KEY", "backup-secret")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://primary.test/v1")
    monkeypatch.setenv("XAI_BASE_URL", "https://backup.test/v1")
    monkeypatch.setenv("OPENAI_ACTOR_AUTHORIZATION", "only-primary")
    monkeypatch.setattr(providers, "circuit", providers.CircuitBreaker())
    original = httpx.AsyncClient
    def install(handler):
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    return install


def test_primary_success_never_calls_backup(transport):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=completion())
    transport(handle)
    assert asyncio.run(providers.answer([{"role": "user", "content": "hi"}])) == ("answer", "gpt")
    assert len(calls) == 1
    assert calls[0].headers["x-openai-actor-authorization"] == "only-primary"
    body = json.loads(calls[0].content)
    assert body["store"] is False


@pytest.mark.parametrize("status", [401, 403, 404, 408, 429, 500, 503])
def test_failover_has_same_context_and_no_primary_header(transport, status):
    calls = []
    def handle(request):
        calls.append(request)
        if request.url.host == "primary.test":
            return httpx.Response(status, json={"error": {"code": "permission_denied" if status == 403 else "unavailable"}})
        return httpx.Response(200, json=completion("backup"))
    transport(handle)
    context = [{"role": "user", "content": "history plus sources"}]
    assert asyncio.run(providers.answer(context)) == ("backup", "xai")
    assert [request.url.host for request in calls] == ["primary.test", "backup.test"]
    assert "x-openai-actor-authorization" not in calls[1].headers
    assert calls[1].headers["authorization"] == "Bearer backup-secret"
    assert json.loads(calls[0].content)["input"] == json.loads(calls[1].content)["input"]
    asyncio.run(providers.answer(context))
    assert [request.url.host for request in calls].count("primary.test") == 1


@pytest.mark.parametrize("status,code", [(400, "bad_request"), (422, "validation"), (403, "content_policy_violation"), (403, "unknown")])
def test_input_and_safety_errors_do_not_fail_over(transport, status, code):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"code": code}})
    transport(handle)
    with pytest.raises(providers.ChatError):
        asyncio.run(providers.answer([]))
    assert len(calls) == 1


def test_connection_error_and_empty_response_can_fail_over(transport):
    for empty in (False, True):
        providers.circuit = providers.CircuitBreaker()
        def handle(request):
            if request.url.host == "primary.test":
                if empty:
                    return httpx.Response(200, json=completion(""))
                raise httpx.ConnectError("test only")
            return httpx.Response(200, json=completion("backup"))
        transport(handle)
        assert asyncio.run(providers.answer([]))[1] == "xai"


def test_circuit_allows_only_one_recovery_probe():
    breaker = providers.CircuitBreaker()
    breaker.failure()
    assert not breaker.claim()
    breaker.until = time.monotonic() - 1
    assert breaker.claim()
    assert not breaker.claim()
    breaker.success()
    assert breaker.claim()


def test_both_providers_fail_with_safe_error(transport):
    transport(lambda request: httpx.Response(503, json={"error": {"message": "secret provider detail"}}))
    with pytest.raises(providers.ChatError) as error:
        asyncio.run(providers.answer([]))
    assert "secret" not in str(error.value)


def test_incomplete_output_is_not_regenerated(transport):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"status": "incomplete", "output": []})
    transport(handle)
    with pytest.raises(providers.ChatError, match="完整"):
        asyncio.run(providers.answer([]))
    assert len(calls) == 1


def test_timeout_is_bounded_and_cancellation_does_not_start_backup(transport, monkeypatch):
    real_positive_int = providers.positive_int
    monkeypatch.setattr(providers, "positive_int", lambda name, default: 0.02 if name == "CHAT_TIMEOUT_SECONDS" else real_positive_int(name, default))
    calls = []
    async def handle(request):
        calls.append(request.url.host)
        if request.url.host == "primary.test":
            await asyncio.sleep(10)
        return httpx.Response(200, json=completion("backup"))
    transport(handle)
    assert asyncio.run(providers.answer([])) == ("backup", "xai")
    assert calls == ["primary.test", "backup.test"]
    providers.circuit = providers.CircuitBreaker()
    calls.clear()
    async def cancel():
        task = asyncio.create_task(providers.answer([]))
        await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel())
    assert calls == ["primary.test"]
