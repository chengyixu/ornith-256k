#!/usr/bin/env python3
"""Shared streaming OpenAI-compatible benchmark helpers."""

from __future__ import annotations

import json
import time
import urllib.request


WORDS = (
    "system module function class return value buffer kernel pipeline latency throughput "
    "memory compute tensor vector matrix layer network gradient optimizer schedule queue "
    "cache index segment offset pointer register thread process signal protocol session "
    "packet socket stream frame block chunk region domain context scope profile metric "
    "benchmark evaluate transform encode decode embed attention normalize aggregate"
).split()


def build_prompt(target_tokens: int) -> str:
    """Build deterministic prose calibrated for the original benchmark harness."""
    word_count = int(target_tokens / 1.483)
    parts = []
    index = 0
    while len(parts) < word_count:
        parts.append(f"{WORDS[index % len(WORDS)]} {WORDS[(index * 7 + 3) % len(WORDS)]}")
        index += 1
    return (
        "Below is a technical log excerpt. Read it carefully.\n\n"
        + " ".join(parts)
        + "\n\nEnd of excerpt. Without summarizing the excerpt, answer: what is 17 * 23? "
        "Reply with just the number."
    )


def run_once(
    url: str,
    model: str,
    prompt: str,
    gen_tokens: int,
    temperature: float,
    top_p: float,
    run_idx: int,
    label: str,
    api_key: str | None = None,
) -> dict[str, int | float | str | None]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": gen_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
    )
    started = time.perf_counter()
    first_token_at = None
    usage = None
    with urllib.request.urlopen(request, timeout=1800) as response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            if event.get("usage"):
                usage = event["usage"]
            choices = event.get("choices") or []
            if choices and (choices[0].get("delta") or {}).get("content") and first_token_at is None:
                first_token_at = time.perf_counter() - started
    total = time.perf_counter() - started
    prompt_tokens = usage.get("prompt_tokens") if usage else None
    completion_tokens = usage.get("completion_tokens") if usage else None
    return {
        "label": label,
        "run": run_idx,
        "prompt_tokens": prompt_tokens,
        "gen_tokens": completion_tokens,
        "ttft_s": round(first_token_at, 3) if first_token_at else None,
        "prefill_tps": round(prompt_tokens / first_token_at, 2)
        if prompt_tokens and first_token_at
        else None,
        "decode_tps": round((completion_tokens - 1) / (total - first_token_at), 2)
        if completion_tokens and first_token_at and total > first_token_at
        else None,
        "total_s": round(total, 2),
    }
