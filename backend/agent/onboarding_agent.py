"""Compatibility entry points for the read-only document assistant."""
from agent.multi_agent import run_multi_agent, stream_multi_agent


def run_agent(message: str, employee_id: str = "", history: list[dict] | None = None):
    return run_multi_agent(message, employee_id, history)


async def stream_agent(message: str, employee_id: str = "", history: list[dict] | None = None):
    async for kind, data in stream_multi_agent(message, employee_id, history):
        if kind == "agent_log":
            yield {"event": "agent_log", "data": data}
        elif kind == "result":
            yield {"event": "citations", "data": data["citations"]}
            text = data["response"]
            for offset in range(0, len(text), 40):
                yield {"event": "token", "data": text[offset:offset + 40]}
            yield {"event": "done", "data": text}
