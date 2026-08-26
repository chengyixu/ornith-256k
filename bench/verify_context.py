#!/usr/bin/env python3
"""Prove a real near-limit context request through the local Ornith API."""

import argparse
import json
import time
import urllib.request
from pathlib import Path

from transformers import AutoTokenizer


SENTINEL = "ORNITH-256K-NEEDLE-7F3A"


def build_prompt(model_dir: Path, minimum_content_tokens: int) -> str:
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    unit_ids = tokenizer.encode(" cache", add_special_tokens=False)
    if not unit_ids:
        raise RuntimeError("Tokenizer produced no filler tokens")

    prefix = "Archive data follows.\n"
    suffix = (
        f"\n\nThe audit sentinel is {SENTINEL}. "
        "Reply with the audit sentinel only."
    )
    fixed_tokens = len(tokenizer.encode(prefix + suffix, add_special_tokens=False))
    filler_count = max(0, minimum_content_tokens - fixed_tokens)
    filler_ids = (unit_ids * ((filler_count + len(unit_ids) - 1) // len(unit_ids)))[
        :filler_count
    ]
    prompt = prefix + tokenizer.decode(filler_ids, skip_special_tokens=False) + suffix
    actual_tokens = len(tokenizer.encode(prompt, add_special_tokens=False))
    if actual_tokens < minimum_content_tokens:
        raise RuntimeError(
            f"Built only {actual_tokens} content tokens; expected at least "
            f"{minimum_content_tokens}"
        )
    return prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--content-tokens", type=int, default=260_000)
    parser.add_argument(
        "--model-dir", type=Path, help="Local tokenizer directory (defaults to base-dir/tokenizer)"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:7871/v1")
    parser.add_argument("--model", default="Ornith-1.5-35B-A3B-Q4_K_M")
    parser.add_argument("--timeout", type=int, default=3_600)
    parser.add_argument(
        "--results-file",
        type=Path,
        help="JSON output path (defaults to base-dir/results/context_256k.json)",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    model_dir = (args.model_dir or base_dir / "tokenizer").resolve()
    settings = json.loads((base_dir / "runtime" / "settings.json").read_text())
    api_key = settings["auth"]["api_key"]
    prompt = build_prompt(model_dir, args.content_tokens)

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        args.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        result = json.loads(response.read())
    elapsed = time.perf_counter() - started

    message = (result.get("choices") or [{}])[0].get("message") or {}
    answer = message.get("content") or ""
    usage = result.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens", 0)
    record = {
        "model": payload["model"],
        "requested_content_tokens": args.content_tokens,
        "server_prompt_tokens": prompt_tokens,
        "completion_tokens": usage.get("completion_tokens"),
        "latency_s": round(elapsed, 2),
        "answer": answer.strip(),
        "sentinel_found": SENTINEL in answer,
        "context_256k_proven": prompt_tokens >= 256_000 and SENTINEL in answer,
    }
    results_file = args.results_file or base_dir / "results" / "context_256k.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    if not record["context_256k_proven"]:
        raise SystemExit("256k context verification failed")


if __name__ == "__main__":
    main()
