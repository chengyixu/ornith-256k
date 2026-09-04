#!/usr/bin/env python3
"""Run reproducible streaming benchmarks against the local Ornith API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
from bench_api import build_prompt, run_once


def task_prompts() -> list[dict[str, object]]:
    source_log = build_prompt(24_000)
    return [
        {
            "label": "short-answer",
            "prompt": (
                "In exactly three concise sentences, explain why a program should validate "
                "input before writing to disk."
            ),
            "gen_tokens": 128,
        },
        {
            "label": "code-gen",
            "prompt": (
                "Write Python code only for a function named merge_intervals that merges "
                "overlapping closed integer intervals. Include type hints, handle unsorted "
                "input, and add three assert examples after the function."
            ),
            "gen_tokens": 512,
        },
        {
            "label": "summarize",
            "prompt": (
                f"{source_log}\n\nSummarize the technical log in exactly eight bullet points. "
                "Each bullet must be at most twelve words."
            ),
            "gen_tokens": 256,
        },
        {
            "label": "long-form",
            "prompt": (
                "Write a detailed practical guide to diagnosing a production memory leak. "
                "Cover observation, reproduction, measurement, mitigation, and prevention. "
                "Use headings and aim for about 700 words."
            ),
            "gen_tokens": 1024,
        },
        {
            "label": "reasoning",
            "prompt": (
                "A service has three sequential stages. Stage A takes 12 ms, stage B takes "
                "18 ms, and stage C takes 30 ms. A and B can run in parallel, but C begins "
                "only after both finish. Calculate the end-to-end latency, explain the critical "
                "path, and state the latency after reducing C by 40%. Show the arithmetic."
            ),
            "gen_tokens": 384,
        },
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:7871/v1")
    parser.add_argument("--model", default="Ornith-1.5-35B-A3B-Q6_K")
    parser.add_argument(
        "--api-key-file", type=Path, default=ROOT / "runtime" / "llama-server-api-keys.txt"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ORNITH_API_KEY", ""),
        help="Optional local llama-server API key; defaults to ORNITH_API_KEY.",
    )
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "raw_streaming.jsonl")
    args = parser.parse_args()

    api_key = args.api_key or (
        args.api_key_file.read_text().strip() if args.api_key_file.is_file() else ""
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.unlink(missing_ok=True)

    for task in task_prompts():
        for run_index in range(args.runs):
            prompt = f"Benchmark request {run_index}:\n\n{task['prompt']}"
            result = run_once(
                args.base_url,
                args.model,
                prompt,
                int(task["gen_tokens"]),
                0,
                1,
                run_index,
                str(task["label"]),
                api_key=api_key,
            )
            with args.output.open("a", encoding="utf-8") as output_file:
                output_file.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
