#!/usr/bin/env python3
"""Verify local research artifacts and their public reproducibility anchors."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reproducibility" / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read())


def verify_local(manifest: dict) -> list[str]:
    failures = []
    model = manifest.get("model", {})
    for field in ("repository", "revision", "filename", "sha256", "size_bytes"):
        if not model.get(field):
            failures.append(f"model.{field} is required")
    if not re.fullmatch(r"[0-9a-f]{40}", str(model.get("revision", ""))):
        failures.append("model.revision must be a 40-character commit SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", str(model.get("sha256", ""))):
        failures.append("model.sha256 must be a SHA-256 digest")

    settings = json.loads((ROOT / "deploy" / "settings.json").read_text())
    if settings["auth"].get("api_key") != "<set-a-local-api-key>":
        failures.append("deploy/settings.json embeds an API key")
    if settings["auth"].get("secret_key") != "<generate-a-local-secret>":
        failures.append("deploy/settings.json embeds a secret key")
    if settings["model"].get("model_dir") != "./models":
        failures.append("deploy/settings.json must use a relative model directory")

    for artifact in manifest.get("artifacts", []):
        path = ROOT / artifact["path"]
        expected = artifact["sha256"]
        if not path.is_file():
            failures.append(f"missing artifact: {artifact['path']}")
        elif sha256(path) != expected:
            failures.append(f"checksum mismatch: {artifact['path']}")
    return failures


def verify_remote(manifest: dict) -> list[str]:
    failures = []
    model = manifest["model"]
    model_info = fetch_json(f"https://huggingface.co/api/models/{model['repository']}")
    if model_info.get("sha") != model["revision"]:
        failures.append("upstream model revision differs from manifest")
    dataset = manifest["dataset"]
    dataset_info = fetch_json(f"https://huggingface.co/api/datasets/{dataset['repository']}")
    if dataset_info.get("sha") != dataset["revision"]:
        failures.append("benchmark dataset revision differs from manifest")
    return failures


def verify_model_file(model_path: Path, manifest: dict) -> list[str]:
    model = manifest["model"]
    failures = []
    if not model_path.is_file():
        return [f"model file does not exist: {model_path}"]
    if model_path.stat().st_size != model["size_bytes"]:
        failures.append("model size differs from manifest")
    if sha256(model_path) != model["sha256"]:
        failures.append("model SHA-256 differs from manifest")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true", help="also verify public Hub revisions")
    parser.add_argument("--model", type=Path, help="verify a downloaded Q6_K model file")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST_PATH.read_text())
    failures = verify_local(manifest)
    if args.remote:
        failures.extend(verify_remote(manifest))
    if args.model:
        failures.extend(verify_model_file(args.model, manifest))
    if failures:
        raise SystemExit("reproducibility verification failed:\n- " + "\n- ".join(failures))
    print("reproducibility bundle verified")


if __name__ == "__main__":
    main()
