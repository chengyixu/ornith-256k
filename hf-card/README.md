---
language: en
license: mit
base_model:
- ornith-ai/Ornith-1.5-35B-A3B-GGUF
tags:
- ornith
- moe
- gguf
- q4_k_m
- long-context
- 256k-context
- apple-silicon
- llama.cpp
- metal
- agentic
- benchmark
inference: false
---

# LocalMoE: Ornith-1.5-35B-A3B Q4_K_M serving configuration for Apple Silicon (verified 262k context)

This repository documents a **measured, reproducible deployment recipe** (no new weights):
Ornith-1.5 35B-A3B sparse MoE at Q4_K_M under **llama.cpp Metal**, tuned and *verified* for
262,144-token agentic workloads on an M4 Max / 64 GB.

## Verified deployment

| Property | Value |
|---|---|
| Model file | `Ornith-1.5-35B-Q4_K_M.gguf` (21,713,463,040 B, SHA-256 `42739874…d41f`) |
| Runtime | llama-server 0.2.0 build 10566, Metal, flash attention |
| K/V cache | q4_0 quantized, one slot, batch 4096 / ubatch 1024 |
| Context | **260,013 prompt tokens proven** with exact sentinel recovery (advertised: 262,144) |
| Endpoint | loopback-only OpenAI-compatible API |

## Measured results (M4 Max, 64 GB, macOS 27.0)

### Streaming profile (cold, median of 3)

| Category | TTFT | Decode |
|---|---|---|
| short-answer | 0.139 s | 86.3 tok/s |
| code-gen | 0.268 s | 48.9 tok/s |
| summarize (32k cold prefill) | 86.278 s | 29.1 tok/s (~376 prompt-tok/s) |
| long-form | 0.357 s | 41.8 tok/s |
| reasoning | 0.348 s | 43.1 tok/s |

Prefix-cache reuse: the same 32k prompt re-served with **0.182 s TTFT** ($474\times$).

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
