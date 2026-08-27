---
language: en
license: mit
base_model:
- ornith-ai/Ornith-1.5-35B-A3B-GGUF
title: LocalMoE: Ornith-1.5-35B-A3A Q6_K (reasoning on) serving recipe for Apple Silicon
tags:
- ornith
- moe
- gguf
- q6_k
- q4_k_m
- metal
- agentic
- long-context
- 256k-context
- apple-silicon
- llama.cpp
- benchmark
inference: false
---

# LocalMoE: Ornith-1.5-35B-A3A Q6_K (+ reasoning) serving recipe for Apple Silicon

This repository documents a **measured, reproducible deployment recipe** (no new weights):
Ornith-1.5 35B-A3B sparse MoE at Q6\_K under **llama.cpp Metal** with reasoning
enabled, tuned and *verified* for 262,144-token agentic workloads on an M4 Max /
64 GB. Previously documented on Q4\_K\_M (reasoning off); upgraded to Q6\_K with
reasoning on to recover capability lost to 4-bit quantization.

## Accepted deployment

| Property | Value |
|---|---|
| Model file | `Ornith-1.5-35B-Q6_K.gguf` (29,208,731,392 B, SHA-256 `15d4658b…b4b`) |
| Runtime | llama-server 0.2.0 build 10566, Metal, flash attention |
| Weights | Q6_K (6-bit) |
| K/V cache | q4_0 quantized, one slot, batch 4096 / ubatch 1024 |
| Context | **260,013 prompt tokens proven** w/ exact sentinel recovery (adv. 262,144) |
| Reasoning | on (`--reasoning on --reasoning-budget 4096`) |
| Endpoint | loopback-only OpenAI-compatible API |

## Measured results (M4 Max, 64 GB, macOS 27.0) — production = Q6_K, reasoning on

### Streaming profile (median of 3)

| Category | TTFT | Decode |
|---|---|---|
| short-answer | 0.049 s | 63.1 tok/s |
| code-gen | 0.048 s | 39.6 tok/s |
| summarize (32k cold prefill) | 0.062 s | 44.3 tok/s |
| long-form | 0.060 s | 44.9 tok/s |
| reasoning | 0.084 s | 23.4 tok/s (incl. chain-of-thought) |

Prior Q4\_K\_M (reasoning off) reached 86.3 tok/s on short-answer and 48.9 tok/s
on code-gen but produced terse, step-skipping answers; Q6 recovers verified
step-by-step reasoning at a moderate speed cost. See
[`paper/main.pdf`](https://github.com/chengyixu/ornith-256k/blob/main/paper/main.pdf)
for the full Q4-vs-Q6 matrix.

Prefix-cache reuse: the same 32k prompt re-served with sub-second TTFT.

### Head-to-head vs dense 27B + DFlash2 speculative decoding (identical prompts)

| Task type | Dense baseline | This configuration |
|---|---|---|
| Decode (median, best category) | 53.7 tok/s | **72.3 tok/s** |
| TTFT (short) | 0.60 s | **0.04 s** |
| Six pi agent tasks | 45–269 s each | **3–21 s each (10–14×)** |

The dense model emits reasoning tokens before answering; its speculation acceptance
collapses on open-ended prose. The MoE pays neither tax.

### Negative results

Embedded NextN/MTP drafting, upstream no-spec builds, and ngram-mod speculation were all
benchmarked in isolated canaries and **rejected** under pre-registered promotion gates —
including a 2% near-limit prefill win that failed the broad-speed requirement.

## Artifacts

- Code, paper (PDF/LaTeX), raw records: [github.com/chengyixu/ornith-256k](https://github.com/chengyixu/ornith-256k)
- Raw measurement dataset: [ChengyiX/ornith-256k-bench](https://huggingface.co/datasets/ChengyiX/ornith-256k-bench)
- Prior dense study: [chengyixu/qwen38-dflash2-bench](https://github.com/chengyixu/qwen38-dflash2-bench)

## Reproduce

```bash
python bench/verify_context.py --content-tokens 260000   # sentinel proof
python bench/bench_raw_suite.py --runs 3                 # streaming suite
bash bench/run_pi_bench.sh                               # agent suite
```

Model weights are subject to the upstream ornith.ai license; this recipe is MIT.
