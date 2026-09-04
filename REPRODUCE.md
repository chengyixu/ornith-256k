# Reproduce the published Ornith measurements

This procedure reconstructs the public Q6_K setup and verifies the paper and
result artifacts without relying on any local model cache, runtime cache, or
credential from the original machine. The historical 260k sentinel result is a
Q4_K_M measurement; Q6_K must re-run the sentinel before it can claim the same
result.

## Verify the publication bundle

```bash
git clone https://github.com/minervacap2022/ornith-256k.git
cd ornith-256k
python3 reproducibility/verify_repro_bundle.py --remote
```

The command verifies the committed paper/result checksums, sanitized public
settings, and the exact public revisions of the model and benchmark dataset.

## Download the Q6_K serving model

Install the Hugging Face CLI, then use the revision and digest in
`reproducibility/manifest.json`:

```bash
hf download ornith-ai/Ornith-1.5-35B-A3B-GGUF \
  Ornith-1.5-35B-Q6_K.gguf \
  --revision 12393612fd4f730ff5aadc23e9b8f9648aa49ceb \
  --local-dir models
shasum -a 256 models/Ornith-1.5-35B-Q6_K.gguf
```

The required digest is
`15d4658bbfc9c6034621729c15bbb50662c82b32a7ddd9624a1e545a74bdbb4b`.
The expected size is 29,208,731,392 bytes.

## Runtime envelope

The reported Q6_K comparison used llama.cpp `bb4caa754` (version 0.2.0,
build 10566), Metal, flash attention, q4_0 K/V cache, one sequence, and a
262,144-token context window on an M4 Max with 64 GB unified memory. Performance
numbers are single-machine measurements, not hardware-independent guarantees.

Build llama.cpp at that revision, bind the server to loopback only, and set a
local API key if authentication is enabled. Pass that key with `ORNITH_API_KEY`
or `--api-key`; the repository intentionally contains no usable credential.

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp && git checkout bb4caa754
cmake -B build -DGGML_METAL=ON
cmake --build build --config Release -j
./build/bin/llama-server \
  -m ../ornith-256k/models/Ornith-1.5-35B-Q6_K.gguf \
  --host 127.0.0.1 --port 7871 \
  -c 262144 -np 1 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0
```

## Re-run the public checks

Install `transformers` to use the bundled tokenizer, then run the context
sentinel and streaming harnesses against the local server:

```bash
python3 bench/verify_context.py \
  --model Ornith-1.5-35B-A3B-Q6_K \
  --content-tokens 260000
python3 bench/bench_raw_suite.py \
  --model Ornith-1.5-35B-A3B-Q6_K --runs 3
```

Compare newly produced records with `results/raw/`. The original Q4_K_M paper
and records remain historical evidence; its exact model is also pinned in the
manifest. The Q6_K addendum is the corrected
`results/raw/head_to_head_streaming_q4vq6_2026-08-27.jsonl` record.
