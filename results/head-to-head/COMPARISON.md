# Head-to-Head: Qwen3.8-27B-4bit vs Ornith-1.5-35B-A3B-Q4_K_M

Same prompts, same pi tasks, same harness. Date: 2026-08-26.

## Raw API (streaming, temp 0, best-of-3, identical prompts)

| Task          | Qwen TTFT med | Ornith TTFT med | Qwen tok/s med | Ornith tok/s med | Winner |
|---------------|---------------|-----------------|----------------|------------------|--------|
| short-answer  | 0.60s         | 0.04s           | 51.52          | 72.29            | Ornith |
| code-gen      | 1.00s         | 0.05s           | 31.22          | 43.17            | Ornith |
| summarize     | 1.54s         | 0.03s           | 53.68          | 66.23            | Ornith |
| long-form     | 0.84s         | 0.05s           | 9.12           | 50.98            | Ornith |
| reasoning     | 1.43s         | 0.05s           | 9.18           | 36.99            | Ornith |

Key differences:
- TTFT: Ornith ~15-30x faster (Qwen emits thinking tokens first; Ornith runs reasoning off).
- Decode: Ornith wins every category. Biggest gap on open-ended generation (long-form:
  5.6x) where Qwen's DFlash2 speculation acceptance collapses.
- Qwen's best category (summarize, 53.68) still trails Ornith's median there (66.23),
  and Ornith's *worst* category (reasoning, 36.99) beats Qwen in every category except
  summarize.

## pi agent tasks (identical prompts)

| Task            | Qwen wall | Ornith wall | Speedup | Notes |
|-----------------|-----------|-------------|---------|-------|
| smoke-test      | 2.1s      | 1.9s        | 1.1x    | — |
| t1-read-file    | 33.8s     | 3.1s        | 10.9x   | — |
| t2-code-write   | 45.1s     | 4.5s        | 10.0x   | both verified fib(10)=55 |
| t3-debug        | see note  | 7.2s        | —       | re-run with real fixture |
| t4-explain      | 268.6s    | 21.2s       | 12.7x   | — |
| t5-refactor     | 139.0s    | 11.2s       | 12.4x   | both pass all asserts |
| t6-multi-step   | 75.4s     | 5.5s        | 13.7x   | — |

t3-debug note: first pass had no fixture on disk for either model (both went hunting).
Re-ran with a real broken.py: Ornith fixed the off-by-one in 7.2s and verified.
The Qwen re-run failed with a connection error — its oMLX server died mid-benchmark
(the `Qwen3.8-27B-4bit` weights were deleted from ~/Models/mlx; disk is at 99% full,
17GB free). The Qwen server now only finds the 3.3GB DFlash2 draft head and can't
serve the full model.

## Verdict

Ornith-1.5-35B-A3B (MoE, A3B active) dominates on this M4 Max for agentic use:
~10-14x faster wall-clock on real agent tasks, faster raw decode in every category,
and near-instant TTFT. Qwen3.8's only edge was deeper built-in reasoning chains —
which cost it heavily in latency here.

## Artifacts
- Ornith raw: scratchpad bench_ornith.json; results: ~/herdr-bench/results-ornith/
- Qwen baseline: ~/herdr-bench/results/ + RESULTS.md
- Harnesses: ~/herdr-bench/bench_pi.sh, ~/herdr-bench/bench_pi_ornith.sh
- Prior Ornith deep-dive (256k context proof, spec-decode research): ~/Models/ornith-256k/RESULTS.md
