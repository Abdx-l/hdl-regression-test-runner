import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from runner import execute, mutate_operator, render, run_suite


class RunnerTests(unittest.TestCase):
    def test_pass_and_failure_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "unit_tb.v").write_text("module unit_tb; endmodule")
            def success(args, **kwargs):
                return subprocess.CompletedProcess(args, 0, "PASS\n" if args[0] == "vvp" else "", "")
            with sqlite3.connect(":memory:") as db:
                rows = run_suite(path, db, command=success)
                self.assertTrue(rows[0]["passed"])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
            self.assertIn("unit_tb.v", render(rows))
            def failure(args, **kwargs):
                return subprocess.CompletedProcess(args, 1, "", "syntax error")
            self.assertFalse(execute(path / "unit_tb.v", [], command=failure)[0])

    def test_mutation_and_timeout(self):
        self.assertEqual(mutate_operator("assign y = a & b;"), "assign y = a | b;")
        def timeout(args, **kwargs):
            raise subprocess.TimeoutExpired(args, 1)
        self.assertIn("timeout", execute("unit_tb.v", [], command=timeout)[2])

