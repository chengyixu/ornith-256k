#!/bin/bash
# Run a pi agent task against the Ornith endpoint, capture timing + output stats.
# Usage: bench_pi_ornith.sh <task-name> "<prompt>"
set -uo pipefail
NAME="$1"; shift
PROMPT="$1"
OUT_DIR="$HOME/herdr-bench/results-ornith"
mkdir -p "$OUT_DIR"
START=$(python3 -c 'import time; print(time.time())')
pi --provider localllm-ornith-256k-llamacpp --model "Ornith-1.5-35B-A3B-Q4_K_M" \
   -p --no-session --no-skills --no-prompt-templates \
   "$PROMPT" > "$OUT_DIR/$NAME.out" 2> "$OUT_DIR/$NAME.err"
RC=$?
END=$(python3 -c 'import time; print(time.time())')
python3 - "$OUT_DIR/$NAME.out" "$OUT_DIR/$NAME.err" "$START" "$END" "$NAME" "$RC" <<'PY' >> "$OUT_DIR/summary.jsonl"
import json, sys
out_path, err_path, start, end, name, rc = sys.argv[1:7]
text = open(out_path, encoding="utf-8", errors="replace").read()
err = open(err_path, encoding="utf-8", errors="replace").read()[-500:]
rec = {
    "task": name, "rc": rc,
    "wall_s": round(float(end) - float(start), 2),
    "output_chars": len(text), "approx_words": len(text.split()),
    "err_tail": err if rc != 0 else "",
}
print(json.dumps(rec))
PY
echo "[$NAME] rc=$RC done in $(python3 -c "print(round($END-$START,1))")s -> $OUT_DIR/$NAME.out"
