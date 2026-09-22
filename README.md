# LocalMoE: Ornith-1.5-35B-A3B on Apple Silicon

[![Paper](https://img.shields.io/badge/paper-PDF-blue)](paper/main.pdf)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Apple%20Silicon-black)]()
[![Runtime](https://img.shields.io/badge/runtime-llama.cpp%20Metal-orange)]()

End-to-end engineering study and reproducible artifacts for serving
**Ornith-1.5-35B-A3B** (35B total / 3B active sparse MoE) on an Apple M4 Max
(64 GB unified memory). The original **Q4_K_M** configuration established the
verified 262,144-token context result; the later **Q6_K** configuration adds a
reasoning-on serving recipe and controlled short-workload comparison.

> Previously documented on Q4_K_M (reasoning off). The Q4 model file was removed
> from disk under storage pressure and replaced with a SHA-256-verified Q6_K
> download; reasoning was enabled to recover the capability lost to the
> aggressive 4-bit quant. See [RESULTS.md](RESULTS.md) for the Q4→Q6 upgrade
> comparison. Raw Q4 records are retained in `results/raw/`.

## Headline results

| Metric | Dense baseline (LocalFlash) | **LocalMoE (this work)** |
|---|---|---|
| Verified context | 260k (dense Qwen3.8) | **260,013 prompt tokens proven w/ Q4_K_M sentinel** |
| TTFT @ short prompt | 0.60 s med | **0.04 s** |
| Decode (median, head-to-head) | 9–54 tok/s by category | **37–72 tok/s**, wins 4/5 categories |
| Agent tasks (6, pi CLI) | 45–269 s each | **3–21 s each (10–14×)** |
| Prefix-cache reuse @ 32k | 8–16 s turn TTFT | **0.18 s** ($474\times$ vs cold) |

All numbers from identical-prompt controlled runs; raw JSON-lines in
[`results/raw/`](results/raw/). Methodology, negative results, and the
head-to-head analysis in [`paper/main.pdf`](paper/main.pdf).

## Why sparse wins for agents

A coding agent makes many model calls per task. The dense reasoning model pays
two taxes on every call: thinking-chain tokens before any visible output, and
speculative-decoding acceptance that collapses on open-ended prose. A 3B-active
MoE pays neither — the result is a compounding 10–14× wall-clock advantage on
real agent tasks even against a dense model accelerated by DFlash 2.

## Negative results (pre-registered promotion gates)

Three speculation candidates were benchmarked and **rejected**:
embedded NextN/MTP drafting, upstream no-spec builds, upstream ngram-mod.
The MTP drafter that produced 809 tok/s on the dense target *regressed* most
categories on the MoE. Full matrix: `results/raw/speed_research_summary.json`.

## Repo layout

```
├── paper/            arXiv-style LaTeX paper (compiles with tectonic)
├── bench/
│   ├── verify_context.py        near-limit sentinel proof (260k)
│   ├── bench_raw_suite.py       streaming suite, cold + cached prefix
│   ├── run_pi_bench.sh          six-task pi agent suite
│   ├── bench_pi.sh              head-to-head pi harness (dense)
│   └── bench_pi_ornith.sh       head-to-head pi harness (MoE)
├── deploy/
│   ├── local-llm.command              production controller
│   ├── settings.json                  llama-server configuration
│   └── omlx-model-settings.example.json
└── results/
    ├── raw/                     all raw measurement records (JSONL/JSON)
    ├── head-to-head/            identical-prompt comparison artifacts
    ├── pi/                      original pi agent suite outputs
    └── *.log                    run logs
```

## Quickstart (reproduce)

```bash
git clone https://github.com/minervacap2022/ornith-256k.git
cd ornith-256k
python3 reproducibility/verify_repro_bundle.py --remote
```

[`REPRODUCE.md`](REPRODUCE.md) pins the public Q4_K_M and Q6_K model revisions
and SHA-256 values, llama.cpp revision, serving parameters, benchmark commands,
and hardware envelope. It is the authoritative clean-machine procedure; the
paper preserves the earlier Q4_K_M long-context experiment and the Q6_K
addendum is documented in the manifest and raw Q4-versus-Q6 record.

## Original-machine controller

The original M4 Max uses one Desktop controller shared with Qwen:

```bash
/Users/wilsonxu/Desktop/local-llm.command ornith start
/Users/wilsonxu/Desktop/local-llm.command ornith status
/Users/wilsonxu/Desktop/local-llm.command ornith test
/Users/wilsonxu/Desktop/local-llm.command ornith stop
```

This convenience controller is not required for reproduction on another host.

## Verification gates (all passed)

1. `/v1/models` + `/slots` expose 262,144-token context ✓
2. Real 260,013-prompt-token request completes with exact sentinel recovery ✓
3. Streaming suite ×5 categories ×3 runs recorded ✓
4. Six pi agent tasks with independently verified filesystem effects ✓
5. Speculation candidates promoted only on broad win + separate context proof — none qualified ✗ (documented)

## Related work

- [chengyixu/qwen38-dflash2-bench](https://github.com/chengyixu/qwen38-dflash2-bench) — the dense LocalFlash baseline this study compares against
- [ornith-ai/Ornith-1.5-35B-A3B-GGUF](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-GGUF) — model weights
- Raw records also mirrored at [ChengyiX/ornith-256k-bench](https://huggingface.co/datasets/ChengyiX/ornith-256k-bench)

## Citation

```bibtex
@misc{klikteam2026localmoe,
  title={Small Active Expert, Big Context Window},
  author={KLIK team},
  year={2026},
  url={https://github.com/chengyixu/ornith-256k}
}
```

## License

MIT — see [LICENSE](LICENSE). Model weights subject to their upstream license.


<!-- minervacap-pre-hiklik-promotion -->
> **Discover Klik:** https://pre.hiklik.ai/
<!-- /minervacap-pre-hiklik-promotion -->
