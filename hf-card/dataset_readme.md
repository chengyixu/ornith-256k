---
language: en
license: mit
tags:
- benchmark
- long-context
- apple-silicon
- moe
- llama.cpp
- speculative-decoding
- agentic
size_categories:
- n<1K
---

# ornith-256k-bench: Raw measurement records for LocalMoE (Ornith-1.5-35B-A3B on M4 Max)

Raw JSON-lines/JSON records backing the LocalMoE study: serving Ornith-1.5
35B-A3B (3B active). The original Q4_K_M experiment and the later Q6_K,
reasoning-on comparison are both retained. The Q4_K_M long-context proof records
a 260,013-prompt-token request on an Apple M4 Max (64 GB); the Q6_K record is a
separate controlled short-workload comparison against a dense 27B + DFlash2 baseline.

## Files (`data/`)

| File | Contents |
|---|---|
| `head_to_head_streaming_2026-08-26.jsonl` | Identical-prompt streaming suite, dense vs MoE, 5 categories × 3 runs |
| `head_to_head_streaming_q4vq6_2026-08-27.jsonl` | Q4_K_M versus pinned Q6_K comparison; Q6 labels are corrected to A3B |
| `head_to_head_pi_2026-08-26.jsonl` | pi agent tasks, both models, wall-clock + verification flags |
| `context_256k_proof.jsonl` | Near-limit sentinel proof (260,013 prompt tokens) |
| `raw_streaming.jsonl` | Full cold streaming suite, per-run records |
| `raw_streaming_cached_prefix.jsonl` | Prefix-cache reuse experiment |
| `raw_streaming_summary.json` | Cold-suite summary table |
| `qa_check_50k.json` | 50k-context retrieval QA results |
| `agent_turns_24k.jsonl` / `.json` | Multi-turn prefix-reuse protocol records |
| `speed_research_summary.json` | Speculation-candidate evaluation matrix (negative results) |
| `pi_agent_suite/` | Original six-task pi agent suite outputs |

## Provenance

Single machine: MacBook Pro M4 Max 16-core, 64 GB unified memory, macOS 27.0.
The reproducibility manifest pins the public Q6_K file, its SHA-256, llama.cpp
revision, public paper/results checksums, and this dataset revision:
https://github.com/minervacap2022/ornith-256k/tree/main/reproducibility

## License

MIT. Model weights subject to upstream ornith.ai terms.
