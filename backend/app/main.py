from __future__ import annotations

import json
import logging
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.multi_agent import run_async
from agent.onboarding_agent import stream_agent
from agent.providers import ChatError
from agent.security import InputValidationError, validate_message_length
from shared.documents import list_documents, read_document
from shared.rag import EmbeddingError

logger = logging.getLogger(__name__)
for log_name in ("agent.providers", "shared.rag"):
    usage_logger = logging.getLogger(log_name)
    if not usage_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        usage_logger.addHandler(handler)
    usage_logger.setLevel(logging.INFO)
    usage_logger.propagate = False
app = FastAPI(title="HR Agent — Harbour Finch Labs", description="聊天與公司文件閱讀", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()],
    allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=200)


def _history(request: ChatRequest) -> list[dict]:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="請先輸入問題。")
    try:
        validate_message_length(request.message)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return [message.model_dump() for message in request.history]


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, (ChatError, EmbeddingError)):
        return str(exc)
    logger.error("chat failed error_type=%s", type(exc).__name__)
    return "暫時未能完成回覆，請稍後再試；你仍可直接閱讀公司文件。"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents")
def documents():
    return {"documents": list_documents()}


@app.get("/api/documents/{filename}")
def source_document(filename: str):
    try:
        return {"filename": filename, "content": read_document(filename)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found") from None


@app.post("/api/chat")
async def chat(request: ChatRequest):
    history = _history(request)
    try:
        return await run_async(request.message, history)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=_safe_error(exc)) from None


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    history = _history(request)

    async def events():
        try:
            async for event in stream_agent(request.message, history=history):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': _safe_error(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
