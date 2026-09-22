"""Offline graph maintenance regressions; fixtures never use the live database."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


GRAPH = Path(__file__).resolve().parents[1]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, GRAPH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(GRAPH), *sys.path]):
        spec.loader.exec_module(module)
    return module


builder = load_module("build_seed")
extract = load_module("extract")
rebuild = load_module("rebuild")


def node(kind, slug, **data):
    return {"type": kind, "data": {"slug": slug, **data}}


def canonicalise(objects):
    return builder.canonicalise([(json.dumps(obj), obj) for obj in objects])


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.seed = self.root / "seed.jsonl"

    def seed_objects(self, objects):
        self.seed.write_text("".join(json.dumps(obj) + "\n" for obj in objects))

    def test_new_runs_preserve_failure_and_retry_provenance(self):
        failed = [json.loads(line) for line in extract.extraction_records("paper", "claims", "failed")]
        retry = [json.loads(line) for line in extract.extraction_records("paper", "claims", "ok")]
        self.assertNotEqual(failed[0]["data"]["slug"], retry[0]["data"]["slug"])
        lines, report = canonicalise([node("Paper", "paper"), *failed, *retry])
        self.assertFalse(report["changed"])
        self.seed.write_text("\n".join(lines) + "\n")
        with patch.object(extract, "SEED_FILE", self.seed):
            *_, completed = extract.load_seed_data()
        self.assertEqual(completed["claims"], {"paper"})
        runs = [json.loads(line)["data"] for line in lines if json.loads(line).get("type") == "Extraction"]
        self.assertEqual({run["result_status"] for run in runs}, {"failed", "ok"})

    def test_legacy_completion_uses_edges_independent_of_record_order(self):
        self.seed_objects([
            {"edge": "HasExtraction", "from": "paper--with-separator", "to": "paper--with-separator--open-questions"},
            node("Extraction", "paper--with-separator--open-questions", mode="open-questions", result_status="ok"),
            node("Paper", "paper--with-separator"),
        ])
        with patch.object(extract, "SEED_FILE", self.seed):
            *_, completed = extract.load_seed_data()
        self.assertEqual(completed["open-questions"], {"paper--with-separator"})

    def test_failed_or_unlinked_runs_do_not_mark_completed(self):
        self.seed_objects([
            node("Paper", "paper"),
            node("Extraction", "paper--claims", mode="claims", result_status="failed"),
            {"edge": "HasExtraction", "from": "paper", "to": "paper--claims"},
            node("Extraction", "paper--figures", mode="figures", result_status="ok"),
        ])
        with patch.object(extract, "SEED_FILE", self.seed):
            *_, completed = extract.load_seed_data()
        self.assertFalse(any(completed.values()))

    def test_valid_empty_result_is_success_not_failure(self):
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"synthetic PDF fixture")
        ctx = {"papers": {"paper": {"title": "Fixture"}}, "concepts": {}, "authors": {}, "techniques": {}}
        with patch.object(extract, "call_gemini", return_value={"extends": [], "contradicts": []}), patch.object(extract, "resolve_paper_slug", return_value="paper"):
            lines = extract.process_paper(pdf, "relations", ctx)
        objects = [json.loads(line) for line in lines]
        self.assertEqual(len(objects), 2)
        self.assertEqual(objects[0]["data"]["result_status"], "ok")
        self.seed_objects([node("Paper", "paper"), *objects])
        with patch.object(extract, "SEED_FILE", self.seed):
            *_, enriched, completed = extract.load_seed_data()
        self.assertFalse(enriched["Extends"])
        self.assertEqual(completed["relations"], {"paper"})

    def test_empty_or_non_object_api_result_records_failure(self):
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"fixture")
        ctx = {"papers": {}, "concepts": {}, "authors": {}, "techniques": {}}
        for result in (None, {}, [], "invalid"):
            with patch.object(extract, "call_gemini", return_value=result):
                lines = extract.process_paper(pdf, "relations", ctx)
            self.assertEqual(json.loads(lines[0])["data"]["result_status"], "failed")

    def test_mode_specific_empty_collections_are_valid(self):
        responses = {
            "metadata": {"authors": [], "concepts": [], "cites_in_collection": []},
            "figures": {"figures": []},
            "claims": {"claims": [], "assumptions": []},
            "relations": {"extends": [], "contradicts": []},
            "methods": {"study_type": [], "techniques": []},
            "definitions": {"definitions": [], "axioms": [], "novel_terms": [], "nonstandard_usage": []},
            "open-questions": {"limitations": [], "open_problems": [], "future_work": [], "tensions": []},
        }
        for mode, response in responses.items():
            with self.subTest(mode=mode):
                extract.validate_response(mode, response)
                with self.assertRaises(ValueError):
                    extract.validate_response(mode, {"error": "Could not analyse this document"})
                missing = dict(response)
                del missing[next(iter(missing))]
                with self.assertRaises(ValueError):
                    extract.validate_response(mode, missing)

    def test_malformed_fields_fail_without_poisoning_completion(self):
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"fixture")
        responses = [
            ("relations", {"error": "Could not analyse this document"}),
            ("relations", {"extends": None, "contradicts": []}),
            ("claims", {"claims": ["scalar"], "assumptions": []}),
            ("claims", {"claims": [{"claim": 42}], "assumptions": []}),
            ("figures", {"figures": [{"id": "Figure 1", "key_data": {}}]}),
            ("methods", {"study_type": [False], "techniques": []}),
        ]
        for mode, response in responses:
            with self.subTest(mode=mode, response=response):
                ctx = {"papers": {"paper": {}}, "concepts": {}, "authors": {}, "techniques": {}}
                with patch.object(extract, "call_gemini", return_value=response):
                    rows = [json.loads(line) for line in extract.process_paper(pdf, mode, ctx)]
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["data"]["result_status"], "failed")
                self.seed_objects([node("Paper", "paper"), *rows])
                with patch.object(extract, "SEED_FILE", self.seed):
                    *_, completed = extract.load_seed_data()
                self.assertFalse(any(completed.values()))

    def test_nonempty_valid_payload_for_every_mode(self):
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"fixture")
        responses = {
            "metadata": ({"authors": [{"name": "First Last"}], "concepts": [{"name": "Concept"}], "cites_in_collection": ["other"], "year": "2026"}, "WrittenBy"),
            "figures": ({"figures": [{"id": "Figure 1", "caption": "A result", "key_data": ["10 Hz"]}]}, "HasFigure"),
            "claims": ({"claims": [{"claim": "Source-backed assertion"}], "assumptions": ["Assumption"]}, "MakesClaim"),
            "relations": ({"extends": [{"slug": "other", "justification": "Development"}], "contradicts": []}, "Extends"),
            "methods": ({"study_type": ["computational"], "techniques": [{"name": "Simulation"}]}, "UsesTechnique"),
            "definitions": ({"definitions": [{"term": "Term", "definition": "Meaning", "formal": False}], "axioms": [], "novel_terms": [], "nonstandard_usage": []}, "HasDefinition"),
            "open-questions": ({"limitations": [{"limitation": "Small sample", "stated_by_authors": True}], "open_problems": [], "future_work": [], "tensions": []}, "Raises"),
        }
        for mode, (response, expected_edge) in responses.items():
            with self.subTest(mode=mode):
                ctx = {"papers": {"paper": {}, "other": {}}, "concepts": {}, "authors": {}, "techniques": {}}
                with patch.object(extract, "call_gemini", return_value=response):
                    rows = [json.loads(line) for line in extract.process_paper(pdf, mode, ctx)]
                self.assertTrue(any(row.get("edge") == expected_edge for row in rows))
                self.assertEqual(next(row["data"]["result_status"] for row in rows if row.get("type") == "Extraction"), "ok")

    def test_handler_failure_preserves_provenance_and_discards_cache_mutations(self):
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"fixture")
        ctx = {"papers": {"paper": {}}, "concepts": {}, "authors": {}, "techniques": {}}

        def broken_handler(response, paper_ctx):
            paper_ctx["authors"]["discard"] = {"name": "Uncommitted output"}
            raise AttributeError("simulated handler failure")

        mode = {**extract.MODES["relations"], "handle_output": broken_handler}
        with patch.dict(extract.MODES, {"relations": mode}), patch.object(extract, "call_gemini", return_value={"extends": [], "contradicts": []}):
            rows = [json.loads(line) for line in extract.process_paper(pdf, "relations", ctx)]
        self.assertEqual(ctx["authors"], {})
        self.assertEqual(rows[0]["data"]["result_status"], "failed")
        self.assertEqual(rows[1]["edge"], "HasExtraction")

    def test_batch_continues_after_malformed_response_and_preserves_both_runs(self):
        paths = {}
        for slug in ("first", "second"):
            paths[slug] = self.root / f"{slug}.pdf"
            paths[slug].write_bytes(b"fixture")
        self.seed_objects([node("Paper", slug) for slug in paths])
        with patch.object(extract, "SEED_FILE", self.seed), patch.object(extract, "find_pdf_path", side_effect=lambda slug, _: paths[slug]), patch.object(extract, "call_gemini", side_effect=[{"error": "bad response"}, {"extends": [], "contradicts": []}]), patch.object(extract, "REQUEST_DELAY_S", 0), patch.object(sys, "argv", ["extract.py", "--all", "--mode", "relations", "--append"]):
            extract.main()
        rows = [json.loads(line) for line in self.seed.read_text().splitlines()]
        runs = [row["data"] for row in rows if row.get("type") == "Extraction"]
        self.assertEqual([run["result_status"] for run in runs], ["failed", "ok"])
        self.assertEqual(len({run["slug"] for run in runs}), 2)
        self.assertFalse(self.seed.with_name("seed.jsonl.write-lock").exists())

    def test_shared_seed_guard_blocks_all_three_maintenance_helpers(self):
        self.seed_objects([node("Paper", "paper")])
        for name in ("readings.pg", "readings.gq"):
            (self.root / name).write_text("fixture")
        with builder.SeedGuard(self.seed):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(builder.main(["--seed", str(self.seed), "--write"]), 2)
            with patch.object(extract, "SEED_FILE", self.seed), patch.object(sys, "argv", ["extract.py", "--all", "--append"]), patch.object(extract, "call_gemini") as api, self.assertRaises(SystemExit):
                extract.main()
            api.assert_not_called()
            with patch.object(rebuild.subprocess, "run") as command, self.assertRaises(RuntimeError):
                rebuild.rebuild(self.root, activate_result=True)
            command.assert_not_called()
        self.assertFalse(self.seed.with_name("seed.jsonl.write-lock").exists())

    def test_guard_contention_from_a_separate_process(self):
        self.seed_objects([node("Paper", "paper")])
        before = self.seed.read_bytes()
        with builder.SeedGuard(self.seed):
            result = subprocess.run([sys.executable, "-B", str(GRAPH / "build_seed.py"), "--seed", str(self.seed), "--write"], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn("already locked", result.stderr)
        self.assertEqual(self.seed.read_bytes(), before)

    def test_external_append_before_canonicalisation_write_is_retained(self):
        self.seed_objects([node("Paper", "paper"), node("Paper", "paper")])
        original_write = builder.write_seed

        def external_edit(path, lines, *, expected):
            with path.open("a") as handle:
                handle.write(json.dumps(node("Paper", "external")) + "\n")
            original_write(path, lines, expected=expected)

        with patch.object(builder, "write_seed", external_edit), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(builder.main(["--seed", str(self.seed), "--write"]), 2)
        self.assertIn('"external"', self.seed.read_text())
        self.assertEqual(len(self.seed.read_text().splitlines()), 3)

    def test_append_guard_rejects_manual_edits_during_a_run(self):
        self.seed_objects([node("Paper", "paper")])
        with builder.SeedGuard(self.seed) as guard:
            guard.append([json.dumps(node("Paper", "first-append"))])
            self.seed.write_text("manual edit\n")
            with self.assertRaises(RuntimeError):
                guard.append([json.dumps(node("Paper", "must-not-append"))])
        self.assertEqual(self.seed.read_text(), "manual edit\n")

    def test_rebuild_uses_snapshot_and_refuses_source_changes_before_activation(self):
        for name in ("readings.pg", "readings.gq", "seed.jsonl"):
            (self.root / name).write_text("original")
        active = self.root / "readings.nano"
        active.mkdir()
        (active / "sentinel").write_text("old database")

        def command(args, **kwargs):
            if args[1] == "init":
                Path(args[3]).mkdir()
            if args[1] == "load":
                data = Path(args[args.index("--data") + 1])
                self.assertNotEqual(data, self.seed)
                self.assertEqual(data.read_text(), "original")
                self.seed.write_text("external change")

        with patch.object(rebuild.subprocess, "run", command), self.assertRaises(RuntimeError):
            rebuild.rebuild(self.root, activate_result=True)
        self.assertEqual((active / "sentinel").read_text(), "old database")
        self.assertEqual(self.seed.read_text(), "external change")
        self.assertFalse(self.seed.with_name("seed.jsonl.write-lock").exists())

    def test_conflicting_assertions_and_legacy_runs_block_writes(self):
        for kind, field in (("Paper", "title"), ("Claim", "claim"), ("Extraction", "result_status")):
            with self.subTest(kind=kind):
                self.seed_objects([node(kind, "same", **{field: "original"}), node(kind, "same", **{field: "proposed"})])
                before = self.seed.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    status = builder.main(["--seed", str(self.seed), "--write"])
                self.assertEqual(status, 2)
                self.assertEqual(self.seed.read_bytes(), before)

    def test_nonconflicting_enrichment_still_unions_and_deduplicates(self):
        self.seed_objects([node("Paper", "paper", title="Original"), node("Paper", "paper", title="Original", thesis="New field")])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(builder.main(["--seed", str(self.seed), "--write"]), 0)
        objects = [json.loads(line) for line in self.seed.read_text().splitlines()]
        self.assertEqual(objects, [node("Paper", "paper", title="Original", thesis="New field")])

    def test_activate_preserves_database_and_refuses_occupied_backup(self):
        stage, active, backup = [self.root / name for name in ("stage", "active", "backup")]
        stage.mkdir()
        active.mkdir()
        (active / "sentinel").write_text("original")
        self.assertEqual(rebuild.activate(stage, active, backup), backup)
        self.assertEqual((backup / "sentinel").read_text(), "original")
        stage.mkdir()
        with self.assertRaises(FileExistsError):
            rebuild.activate(stage, active, backup)
        self.assertTrue(stage.is_dir())

    def test_failed_activation_restores_old_database(self):
        stage, active, backup = [self.root / name for name in ("stage", "active", "backup")]
        stage.mkdir()
        active.mkdir()
        (active / "sentinel").write_text("original")
        rename = Path.rename

        def fail_stage(path, target):
            if path == stage:
                raise OSError("simulated activation failure")
            return rename(path, target)

        with patch.object(Path, "rename", fail_stage), self.assertRaises(OSError):
            rebuild.activate(stage, active, backup)
        self.assertEqual((active / "sentinel").read_text(), "original")
        self.assertTrue(stage.is_dir())

    def test_validation_failure_keeps_active_database(self):
        for name in ("readings.pg", "readings.gq", "seed.jsonl"):
            (self.root / name).write_text("fixture")
        active = self.root / "readings.nano"
        active.mkdir()
        (active / "sentinel").write_text("original")
        with patch.object(rebuild.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "nanograph")), self.assertRaises(subprocess.CalledProcessError):
            rebuild.rebuild(self.root, activate_result=True)
        self.assertEqual((active / "sentinel").read_text(), "original")
        self.assertFalse((self.root / "readings.nano.rebuild-lock").exists())

    def test_existing_lock_prevents_build(self):
        for name in ("readings.pg", "readings.gq", "seed.jsonl"):
            (self.root / name).write_text("fixture")
        (self.root / "readings.nano.rebuild-lock").mkdir()
        with patch.object(rebuild.subprocess, "run") as run, self.assertRaises(FileExistsError):
            rebuild.rebuild(self.root, activate_result=True)
        run.assert_not_called()

    def test_activation_refuses_symlink(self):
        stage, active, backup, target = [self.root / name for name in ("stage", "active", "backup", "target")]
        stage.mkdir()
        target.mkdir()
        active.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            rebuild.activate(stage, active, backup)
        self.assertTrue(active.is_symlink())
        self.assertFalse(backup.exists())

    @unittest.skipUnless(shutil.which("nanograph"), "Nanograph is not installed")
    def test_real_nanograph_bootstrap_and_rebuild_in_temporary_directory(self):
        (self.root / "readings.pg").write_text("node Paper {\n slug: String @key\n}\n")
        (self.root / "readings.gq").write_text("query allPapers() {\n match { $p: Paper }\n return { $p.slug }\n}\n")
        self.seed_objects([node("Paper", "fixture")])
        stage = rebuild.rebuild(self.root)
        self.assertTrue(stage.is_dir())
        self.assertFalse((self.root / "readings.nano").exists())
        active = rebuild.rebuild(self.root, activate_result=True)
        self.assertTrue(active.is_dir())
        rebuild.rebuild(self.root, activate_result=True)
        self.assertEqual(len(list(self.root.glob("readings.nano.backup-*"))), 1)
        self.assertFalse((self.root / "nanograph.toml").exists())
        self.assertFalse((self.root / ".env.nano").exists())
        subprocess.run(["nanograph", "doctor", "--db", str(active), "--schema", str(self.root / "readings.pg")], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
