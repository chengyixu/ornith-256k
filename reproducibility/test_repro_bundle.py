import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityBundleTest(unittest.TestCase):
    def test_manifest_pins_public_model_and_artifacts(self):
        manifest = json.loads((ROOT / "reproducibility" / "manifest.json").read_text())

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["model"]["repository"], "ornith-ai/Ornith-1.5-35B-A3B-GGUF")
        self.assertEqual(manifest["model"]["revision"], "12393612fd4f730ff5aadc23e9b8f9648aa49ceb")
        self.assertEqual(manifest["model"]["filename"], "Ornith-1.5-35B-Q6_K.gguf")
        self.assertEqual(
            manifest["model"]["sha256"],
            "15d4658bbfc9c6034621729c15bbb50662c82b32a7ddd9624a1e545a74bdbb4b",
        )
        self.assertGreater(manifest["model"]["size_bytes"], 29_000_000_000)

        self.assertTrue(manifest["artifacts"])
        for artifact in manifest["artifacts"]:
            self.assertTrue((ROOT / artifact["path"]).is_file())
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")

    def test_public_settings_do_not_embed_runtime_credentials(self):
        settings = json.loads((ROOT / "deploy" / "settings.json").read_text())

        self.assertEqual(settings["auth"]["api_key"], "<set-a-local-api-key>")
        self.assertEqual(settings["auth"]["secret_key"], "<generate-a-local-secret>")
        self.assertEqual(settings["model"]["model_dir"], "./models")

    def test_benchmark_harness_has_no_sibling_checkout_dependency(self):
        harness = (ROOT / "bench" / "bench_raw_suite.py").read_text()

        self.assertNotIn("qwen38-dflash2-bench", harness)
        self.assertNotIn("sys.path.insert", harness)
        self.assertTrue((ROOT / "bench" / "bench_api.py").is_file())

    def test_reproduction_guide_links_the_manifest_and_exact_model(self):
        guide = (ROOT / "REPRODUCE.md").read_text()

        self.assertIn("reproducibility/manifest.json", guide)
        self.assertIn("15d4658bbfc9c6034621729c15bbb50662c82b32a7ddd9624a1e545a74bdbb4b", guide)
        self.assertIn("12393612fd4f730ff5aadc23e9b8f9648aa49ceb", guide)

    def test_q6_does_not_claim_the_historical_q4_context_proof(self):
        manifest = json.loads((ROOT / "reproducibility" / "manifest.json").read_text())
        q4 = manifest["historical_q4_context_proof"]

        self.assertEqual(q4["filename"], "Ornith-1.5-35B-Q4_K_M.gguf")
        self.assertEqual(q4["evidence"], "results/raw/context_256k_proof.jsonl")
        self.assertIn("Q4\\_K\\_M", (ROOT / "RESULTS.md").read_text())

    def test_bridge_smoke_test_is_tracked_and_credential_free(self):
        smoke_test = (ROOT / "tests" / "gemini-openai-bridge.e2e.mjs").read_text()
        bridge = ROOT / "runtime" / "gemini-openai-bridge.mjs"

        self.assertTrue(bridge.is_file())
        self.assertIn("GEMINI_API_KEY", smoke_test)
        self.assertNotIn("llama-server-api-keys.txt", smoke_test)

    def test_controller_uses_relative_paths_and_a_completion_probe(self):
        controller = (ROOT / "deploy" / "ornith-local-model.command").read_text()

        self.assertIn('PROJECT_ROOT="${ORNITH_PROJECT_ROOT:-$(cd', controller)
        self.assertIn('LLAMA_API_KEY_FILE="${PROJECT_ROOT}/runtime/llama-server-api-keys.txt"', controller)
        self.assertIn("llama_probe_status()", controller)
        self.assertIn('chat_template_kwargs: { enable_thinking: false }', controller)


if __name__ == "__main__":
    unittest.main()
