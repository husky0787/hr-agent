"""Explicit, small live API smoke test. Uses configured keys; never prints them.

Run from the repository: python scripts/smoke_api.py [--fallback] [--concurrent]
Optional `psutil` adds process RAM samples. Results go to ignored data/api-smoke.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fallback", action="store_true", help="Simulate GPT failure and use real xAI")
    parser.add_argument("--concurrent", action="store_true", help="Also test two concurrent live turns")
    args = parser.parse_args()
    try:
        import psutil
        process = psutil.Process()
    except ImportError:
        process = None
    report = {"checks": [], "ram_mb": {}}
    started = time.monotonic()
    cpu_before = process.cpu_times() if process else None
    def memory(label):
        if process:
            report["ram_mb"][label] = round(process.memory_info().rss / 1024**2, 1)
    memory("before_import")
    from agent import providers
    from agent.multi_agent import run_async
    from shared import rag
    from shared.config import DATA_DIR
    memory("after_import")
    peak = [process.memory_info().rss if process else 0]
    stop = threading.Event()
    def sample():
        while not stop.wait(0.05):
            if process:
                peak[0] = max(peak[0], process.memory_info().rss)
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    async def question(label, text):
        started = time.monotonic()
        result = await run_async(text)
        row = {"check": label, "provider": result.get("provider"),
               "seconds": round(time.monotonic() - started, 2),
               "correct_policy": "25" in result["response"],
               "cited_handbook": "employee-handbook.md" in result["citations"]}
        report["checks"].append(row)
        print(json.dumps(row), flush=True)
        assert row["correct_policy"] and row["cited_handbook"], "Live policy answer did not meet smoke expectations"
    try:
        await asyncio.to_thread(rag.ensure_index)
        memory("after_index")
        providers.circuit.success()
        await question("default", "員工每年有多少天有薪年假？")
        memory("after_answer")
        if args.fallback:
            original = providers._request
            async def fail_primary(provider, messages):
                if provider.name == "gpt":
                    raise providers.ChatError("Simulated outage", fallback=True, category="smoke_outage")
                return await original(provider, messages)
            providers._request = fail_primary
            providers.circuit.success()
            try:
                await question("forced_gpt_outage", "員工每年有多少天有薪年假？")
                assert report["checks"][-1]["provider"] == "xai"
            finally:
                providers._request = original
                providers.circuit.success()
        if args.concurrent:
            await asyncio.gather(question("concurrent_1", "員工每年有多少天有薪年假？"),
                                 question("concurrent_2", "How many days of paid annual leave do employees receive?"))
        memory("idle_after_calls")
        report["forbidden_modules_loaded"] = [name for name in ("torch", "sentence_transformers", "psycopg", "shared.db") if name in sys.modules]
        assert not report["forbidden_modules_loaded"]
        report["index_bytes"] = sum(path.stat().st_size for path in Path(rag.CHROMA_PATH).rglob('*') if path.is_file())
        if process:
            report["ram_mb"]["sampled_peak"] = round(max(peak[0], process.memory_info().rss) / 1024**2, 1)
            cpu_after = process.cpu_times()
            report["cpu_seconds"] = round(cpu_after.user + cpu_after.system - cpu_before.user - cpu_before.system, 3)
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        target = DATA_DIR / "api-smoke.json"
        target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ram_mb": report["ram_mb"], "forbidden_modules_loaded": report["forbidden_modules_loaded"]}), flush=True)
    finally:
        stop.set()
        sampler.join(timeout=1)


if __name__ == "__main__":
    asyncio.run(main())
