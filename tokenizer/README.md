---
library_name: mlx
tags:
- mlx
- oq
- quantized
- benchmark
- performance
- mtp
- moe
- ornith
---

# Ornith-1.5-35B-A3B-oQ4e-mtp

This model was quantized using [oQ](https://github.com/jundot/omlx) (oMLX v0.6.2) mixed-precision quantization.

Base model: [ornith-ai/Ornith-1.5-35B-A3B](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B)

Chat template: [froggeric/Qwen-Fixed-Chat-Templates](https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates/tree/main) (v21.3, original backed up as `chat_template.jinja.bak`)

## Quantization details

- **Model type**: qwen3_5_moe
- **Bits**: 4
- **Group size**: 64
- **Mode**: affine
- **Format**: MLX safetensors
- **MTP**: Preserved (mtp_num_hidden_layers: 1 — built-in MTP head, no external donor)
- **Calibration**: oQ4e (enhanced, imatrix-based)
- **Note**: text-only variant (vision tower dropped, −0.89 GB) to keep the MTP head intact

## Environment

- **Hardware**: M5 MacBook Air 32GB
- **Inference Framework**: oMLX v0.6.2
- **Max Concurrent Requests**: 4
- **Settings**:
  - Thinking: Disabled
  - TurboQuant KV Cache: Enabled (4-bit)
  - Lightning MTP: Disabled (recommended — see note below)

> ⚠️ **Lightning MTP**
>
> **中文**：本模型建议**不要开启** Lightning MTP。MoE 架构模型 MTP 效果有差异，请先自行测试再决定是否开启。本卡的性能与智能基准数据均在不开启 Lightning MTP 的情况下测得。
>
> **English**: For this model it is recommended to **leave Lightning MTP disabled**. MTP effectiveness varies across MoE-architecture models — test on your own setup before deciding whether to enable it. All benchmark results on this card were measured with Lightning MTP off.

## Performance Benchmarks

> **Note**: Results are for reference only and may vary depending on hardware, software configuration, and workload.

### Single Request Results

| Test | TTFT(ms) | TPOT(ms) | pp TPS | tg TPS | E2E(s) | Throughput | Peak Mem |
|------|----------|----------|--------|--------|--------|------------|----------|
| pp1024/tg128 | 1144.8 | 23.23 | 894.5 tok/s | 43.4 tok/s | 4.109 | 280.4 tok/s | 20.15 GB |
| pp4096/tg128 | 3837.4 | 23.87 | 1067.4 tok/s | 42.2 tok/s | 6.884 | 613.6 tok/s | 20.86 GB |

### Continuous Batching (pp1024 / tg128)

| Batch | tg TPS | Speedup | pp TPS | pp TPS/req | TTFT(ms) | E2E(s) |
|-------|--------|---------|--------|------------|----------|--------|
| 1x | 43.4 tok/s | 1.00x | 894.5 tok/s | 894.5 tok/s | 1144.8 | 4.109 |
| 2x | 63.3 tok/s | 1.46x | 623.0 tok/s | 311.5 tok/s | 2689.4 | 7.331 |
| 4x | 99.9 tok/s | 2.30x | 515.0 tok/s | 128.8 tok/s | 4742.9 | 13.081 |

## Intelligence Benchmark

> **Note**: Each benchmark round tests only 30 questions. Results are for reference only.

| Benchmark | Accuracy | Correct | Total | Time(s) | Think |
|-----------|----------|---------|-------|---------|-------|
| MMLU | 56.7% | 17 | 30 | 70.5 | No |
| TRUTHFULQA | 96.7% | 29 | 30 | 18.9 | No |
| GSM8K | 96.7% | 29 | 30 | 99.0 | No |
| MATHQA | 53.3% | 16 | 30 | 71.9 | No |
| HUMANEVAL | 73.3% | 22 | 30 | 81.3 | No |
