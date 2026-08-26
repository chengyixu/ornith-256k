#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$ROOT/pi-bench-workspace/tasks"
OUT_DIR="$ROOT/results/pi"
PROVIDER="localllm-ornith-256k-llamacpp"
MODEL="Ornith-1.5-35B-A3B-Q4_K_M"

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR" "$OUT_DIR"
: > "$OUT_DIR/summary.jsonl"

cat > "$WORK_DIR/broken.py" <<'PY'
def total(values: list[int]) -> int:
    return sum(values) - 1


if total([1, 2, 3]) != 6:
    raise AssertionError("total must sum all values")
PY

cat > "$WORK_DIR/package.json" <<'JSON'
{
  "name": "agent-benchmark-fixture",
  "version": "1.0.0",
  "description": "A small fixture for agent explanation tests.",
  "type": "module",
  "scripts": {"test": "node test.js"},
  "dependencies": {"left-pad": "1.3.0"}
}
JSON

cat > "$WORK_DIR/refactor_demo.py" <<'PY'
class Calculator:
    def add(self, left: int, right: int) -> int:
        return left - right

    def subtract(self, left: int, right: int) -> int:
        return left + right

    def multiply(self, left: int, right: int) -> int:
        return left * right - 1


def run_tests() -> None:
    assert Calculator().add(2, 3) == 5
    assert Calculator().subtract(5, 3) == 2
    assert Calculator().multiply(4, 3) == 12


if __name__ == "__main__":
    run_tests()
PY

run_task() {
  local name="$1"
  local prompt="$2"
  local started ended exit_code
  started="$(python3 -c 'import time; print(time.time())')"
  set +e
  (
    cd "$WORK_DIR"
    PI_OFFLINE=1 pi --provider "$PROVIDER" --model "$MODEL" \
      -p --no-session --no-skills --no-prompt-templates "$prompt"
  ) > "$OUT_DIR/$name.out" 2> "$OUT_DIR/$name.err"
  exit_code=$?
  set -e
  ended="$(python3 -c 'import time; print(time.time())')"
  python3 - "$OUT_DIR/$name.out" "$OUT_DIR/$name.err" "$started" "$ended" "$name" "$exit_code" <<'PY' >> "$OUT_DIR/summary.jsonl"
import json
import sys

out_path, err_path, started, ended, name, exit_code = sys.argv[1:7]
text = open(out_path, encoding="utf-8", errors="replace").read()
err = open(err_path, encoding="utf-8", errors="replace").read()[-500:]
print(json.dumps({
    "task": name,
    "rc": int(exit_code),
    "wall_s": round(float(ended) - float(started), 2),
    "output_chars": len(text),
    "approx_words": len(text.split()),
    "err_tail": err if int(exit_code) != 0 else "",
}))
PY
  printf '[%s] exit=%s\n' "$name" "$exit_code"
  return "$exit_code"
}

run_task "t1-read-file" "List the top-level entries in the current directory, identify whether each is a file or directory, and do not modify anything."
run_task "t2-code-write" "Create fib.py with an iterative fib(n) function. It must return fib(10) == 55, reject negative n with ValueError, and run a verification command before answering."
run_task "t3-debug" "Find and fix the bug in broken.py. Do not change the expected test behavior. Run broken.py after the fix and report the observed result."
run_task "t4-explain" "Explain every top-level key in package.json concisely, using the actual fixture values. Do not modify files."
run_task "t5-refactor" "Refactor refactor_demo.py by fixing its Calculator behavior. Do not weaken or remove the assertions. Run the file and report whether all assertions pass."
run_task "t6-multi-step" "Run these shell steps in order: echo hello; create nums.txt with lines 1 through 5; sort it numerically; count its lines. Report all observed outputs."
