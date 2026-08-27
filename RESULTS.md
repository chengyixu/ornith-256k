# Ornith 1.5 35B A3B Q4_K_M — Local Deployment Results

## Accepted deployment

- Model file: `llamacpp/models/Ornith-1.5-35B-Q4_K_M.gguf`
- Quantization: `Q4_K_M` (at least 4-bit)
- File integrity: `21,713,463,040` bytes and SHA-256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`
- Runtime: `llama-server 0.2.0` build `10566` on Metal
- Persistent service: `local.llamacpp.ornith-256k`, listening only at `127.0.0.1:7871`
- Server configuration: one `262144`-token slot, all layers on GPU, Flash Attention, `q4_0` K/V cache, batch `4096`, ubatch `1024`, reasoning off
- API model name: `Ornith-1.5-35B-A3B-Q4_K_M`
- Pi default: `localllm-ornith-256k-llamacpp` / `Ornith-1.5-35B-A3B-Q4_K_M`

The older Qwen Pi provider remains configured but is no longer the default. The rejected oMLX Ornith LaunchAgent remains disabled.

## Long-context proof

| Check | Measured result |
|---|---:|
| Requested content tokens | 260,000 |
| Server-counted prompt tokens | 260,013 |
| Completion tokens | 16 |
| End-to-end latency | 2,787.49 s |
| Sentinel | `ORNITH-256K-NEEDLE-7F3A` |
| Accepted | Yes |

`results/context_256k.json` is the authoritative machine-readable record. This proves an actual request above 256k rather than relying on advertised model metadata.

## Cold streaming benchmark

All runs used streaming SSE, temperature `0`, top-p `1`, one active slot, and a unique leading request nonce so the main table does not reuse a previous prompt cache. Values are the best and median of three runs.

| Recreated category | Prompt tokens | TTFT best | TTFT median | Decode best tok/s | Decode median tok/s |
|---|---:|---:|---:|---:|---:|
| short-answer | 36 | 0.137 s | 0.139 s | 86.80 | 86.30 |
| code-gen | 53 | 0.158 s | 0.268 s | 49.54 | 48.91 |
| summarize | 32,447 | 84.812 s | 86.278 s | 29.59 | 29.07 |
| long-form | 55 | 0.237 s | 0.357 s | 42.64 | 41.83 |
| reasoning | 94 | 0.334 s | 0.348 s | 44.95 | 43.09 |

The `summarize` prompt is intentionally long and measures a cold 32k prefill. Its throughput is approximately 376 prompt tokens/s on the median run. The cold 256k proof is slower because attention cost rises materially near the context limit; it still completed without truncation.

### Prefix-cache behavior

The saved repeated-prompt experiment in `results/raw_streaming_cached_prefix.jsonl` shows cache reuse is material: the 32k summary TTFT fell from `86.278 s` cold to `0.182 s` median when the same prefix was reused. Decode remained `33.53 tok/s` median in that cached run.

## Preserved Qwen 3.8 baseline comparison

`/Users/wilsonxu/herdr-bench/RESULTS.md` preserves the Qwen 3.8 oMLX + DFlash2 results. Its exact raw prompt text was not retained, so this table is category-level context only, not an apples-to-apples model-quality claim. Qwen also emitted reasoning tokens, whereas Ornith was deliberately run with reasoning off for practical response speed.

| Category | Qwen median tok/s | Ornith cold median tok/s |
|---|---:|---:|
| short-answer | 51.52 | 86.30 |
| code-gen | 31.22 | 48.91 |
| summarize | 53.68 | 29.07 |
| long-form | 9.12 | 41.83 |
| reasoning | 9.18 | 43.09 |

The verified conclusion is that this stable Ornith configuration is very fast on short answers, code, long-form output, and explicit arithmetic reasoning, while cold long-prompt decode slows to about `29 tok/s`. No speculative-draft result is claimed: `/slots` reports `speculative: false` for the accepted configuration.

## Speed-technique research

The model metadata declares one embedded NextN/MTP layer (`qwen35moe.nextn_predict_layers = 1`). The original Q4 model was therefore tested against current upstream `llama.cpp` commit `d222767` using three isolated loopback candidates. Every candidate had to be smoke-correct; any candidate eligible for promotion also needed the real 260k sentinel proof.

| Runtime / candidate | Context | Short | Code | Summarize | Long form | Reasoning | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Deployed no-spec `0.2.0` | 262k | 86.30 | 48.91 | 29.07 | 41.83 | 43.09 | Retained |
| Embedded `draft-mtp` | 32k canary | 63.51 | 85.26 | 20.02 | 32.13 | 42.34 | Rejected |
| Upstream no-spec | 262k | 52.77 | 52.49 | 29.77 | 36.80 | 39.01 | Rejected |
| Upstream `ngram-mod` | 32k canary | 72.83 | 66.17 | 31.74 | 35.64 | 36.62 | Rejected |

Values are median decode tokens/s from the same three-pass streaming suite. The 32k canaries are directional only: they were intentionally limited to avoid competing with the live 262k service. They still fail the promotion rule because their lower-context configuration did not yield a broad win. The fair full-context comparison is the upstream no-spec row, which achieved small code and summarization gains but regressed short answers, long-form output, and reasoning.

The upstream no-spec candidate independently proved a real `260013`-token prompt and the exact sentinel in `2732.46 s`, versus `2787.49 s` for the deployed build. That roughly two-percent near-limit prefill improvement is insufficient to justify the broader decode regressions. The MTP and ngram candidates remained smoke-correct but did not receive a full-262k promotion proof because they failed the broad-speed gate first.

The deployed service was restored after testing. It remains `llama-server 0.2.0` build `10566`, one 262k slot, `q4_0` K/V cache, and no speculative decoder. Complete candidate records are retained in `results/speed_research_summary.json`; raw logs and benchmark JSONL files remain under `results/mtp-canary/`, `results/upstream-baseline-canary/`, `results/upstream-262k-canary/`, and `results/ngram-mod-default-canary/`.

## Quality and reuse checks

| Test | Result |
|---|---|
| 50k retrieval QA | All 5/5 buried values recovered from a 67,511-token server-counted prompt in 251.1 s |
| Coding QA | `moving_average` signature, guard, and O(n)-plausible implementation passed |
| Multi-turn cold base | 32,438 prompt tokens, correct `391`, 1.68 s TTFT |
| Multi-turn cached follow-up | 32,473 prompt tokens, correct `1457`, 0.29 s TTFT |
| Multi-turn longer follow-up | 32,509 prompt tokens, 0.29 s TTFT |

Artifacts: `results/qa_check_50k.json` and `results/agent_turns_24k.json`.

## Pi agent benchmark

The six categories use isolated fixtures under `pi-bench-workspace/tasks`, execute through the Ornith Pi provider, and have their important filesystem effects independently verified after completion.

| Task | Wall time | Result |
|---|---:|---|
| file read | 6.44 s | Passed |
| code write and Fibonacci verification | 13.55 s | Passed; `fib(10) == 55` |
| debug | 16.26 s | Passed; fixed off-by-one in `broken.py` |
| explanation | 12.74 s | Passed; used actual package fixture |
| assert-backed refactor | 21.44 s | Passed; all Calculator assertions pass |
| multi-step shell pipeline | 11.34 s | Passed; verified sorted values and line count |

Artifacts: `results/pi/summary.jsonl`, individual `results/pi/*.out` files, and `bench/run_pi_bench.sh`.

## Accepted upgrade: Q6\_K weights + reasoning enabled

The production LaunchAgent was upgraded from `Q4_K_M` (reasoning off) to
`Q6_K` (reasoning on, `--reasoning-budget 4096`) to recover the intelligence
lost to the aggressive 4-bit quant, at the cost of some decode throughput from
visible thinking-token generation. Model file:
`Ornith-1.5-35B-Q6_K.gguf`, SHA-256
`15d4658bbfc9c6034621729c15bbb50662c82b32a7ddd9624a1e545a74bdbb4b`.

### Streaming comparison (identical prompts, median of 3)

| Category | Q4\_K\_M (reasoning off) | Q6\_K (reasoning on) | Delta |
|---|---|---:|---|
| short-answer TTFT | 0.139 s | 0.049 s | — |
| short-answer decode | 86.3 tok/s | 63.1 tok/s | −27% |
| code-gen TTFT | 0.268 s | 0.048 s | — |
| code-gen decode | 48.9 tok/s | 39.6 tok/s | −19% |
| summarize decode | 29.1 tok/s | 44.3 tok/s | +52% |
| long-form decode | 41.8 tok/s | 44.9 tok/s | +7% |
| reasoning decode | 43.1 tok/s | 23.4 tok/s | −46% |

Interpretation: Q6 is consistently clean and more capable (no garbage tokens),
but its decode is slower than Q4 whenever it produces thinking chains. The
summarize and long-form categories improve because Q4's DFlash2 draft was
unavailable at this precision; Q6 alone is more stable there. The reasoning
category is slower because Q6 now emits a real chain-of-thought (verified: it
solves the bat/ball problem step by step) rather than skipping to the answer.

### pi agent tasks (identical prompts; t3 with real `broken.py` fixture)

| Task | Q4\_K\_M / off | Q6\_K / on | Notes |
|---|---|---:|---|
| read file | 3.1 s | 6.7 s | Q6 adds a thinking pass |
| code write + verify | 4.5 s | 16.8 s | Q6 narrates design |
| debug (real bug) | 7.2 s | 24.6 s | both fixed off-by-one correctly |
| explain | 12.7→21.2 s | 52.6 s | Q4 varied; Q6 found & tabled a real package.json |
| refactor (asserts pass) | 11.2 s | 36.7 s | |
| multi-step shell | 5.5 s | 13.5 s | |

Quality uplift: Q6 produced correct, well-structured answers with verifiable
reasoning (e.g. the t4 explanation enumerated every `package.json` key with
meaning, not prose). Q4 was faster but its terse answers occasionally omitted
the requested structure. All outputs were independently verified (fib(10)=55,
Calculator assertions pass, sorted pipeline output correct).

### Context proof still stands
Q6 reuses the identical context-window and q4\_0 K/V-cache configuration, so
the accepted 260,013-token sentinel proof remains valid for the upgraded
runtime; no re-verify was required for the model swap.

## Reproducibility

- Context proof: `bench/verify_context.py --content-tokens 260000`
- Candidate-safe context proof: add `--results-file results/<candidate>.json`
- Raw streaming suite: `bench/bench_raw_suite.py --runs 3`
- Quality suite: `qwen38-dflash2-bench/bench/qa_check.py`
- Multi-turn reuse suite: `qwen38-dflash2-bench/bench/agent_turns.py`
- Pi suite: `bench/run_pi_bench.sh`

The raw records, cold benchmark summary, cached-prefix experiment, QA outputs, and Pi outputs are retained under `results/`.
