"""Run Verilog benches, persist outcomes and render an HTML report."""
import argparse
import html
import re
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path


SCHEMA = """CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,bench TEXT,passed INTEGER,seconds REAL,output TEXT,created_at REAL);"""


def mutate_operator(source):
    for before, after in ((" & ", " | "), (" | ", " & "), (" + ", " - ")):
        if before in source:
            return source.replace(before, after, 1)
    raise ValueError("no supported operator found")


def execute(bench, sources, timeout=10, command=subprocess.run):
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as folder:
        binary = str(Path(folder) / "test.vvp")
        try:
            compile_result = command(["iverilog", "-o", binary, *map(str, sources), str(bench)], capture_output=True, text=True, timeout=timeout)
            if compile_result.returncode:
                return False, time.monotonic() - start, "compile failed\n" + compile_result.stderr
            result = command(["vvp", binary], capture_output=True, text=True, timeout=timeout)
            output = result.stdout + result.stderr
            failed = re.search(r"^FAIL:\s*.+", output, re.MULTILINE)
            passed = result.returncode == 0 and failed is None and re.search(r"^PASS\s*$", output, re.MULTILINE) is not None
            return passed, time.monotonic() - start, output
        except subprocess.TimeoutExpired:
            return False, time.monotonic() - start, f"timeout after {timeout}s"


def run_suite(folder, db, timeout=10, command=subprocess.run):
    folder = Path(folder)
    benches = sorted(folder.glob("*_tb.v"))
    if not benches:
        raise ValueError("no *_tb.v files found")
    sources = sorted(p for p in folder.glob("*.v") if not p.name.endswith("_tb.v"))
    db.executescript(SCHEMA)
    rows = []
    for bench in benches:
        passed, seconds, output = execute(bench, sources, timeout, command)
        db.execute("INSERT INTO runs(bench,passed,seconds,output,created_at) VALUES(?,?,?,?,?)", (bench.name, int(passed), seconds, output, time.time()))
        rows.append({"bench": bench.name, "passed": passed, "seconds": seconds, "output": output})
    db.commit()
    return rows


def render(rows):
    body = ['<!doctype html><meta charset="utf-8"><title>HDL Regression</title>', '<style>body{font:16px system-ui;max-width:900px;margin:3rem auto}th,td{padding:.6rem;border-bottom:1px solid #ddd;text-align:left}pre{white-space:pre-wrap}</style>', '<h1>HDL Regression</h1><table><tr><th>Bench</th><th>Result</th><th>Seconds</th><th>Output</th></tr>']
    for row in rows:
        body.append(f'<tr><td>{html.escape(row["bench"])}</td><td>{"PASS" if row["passed"] else "FAIL"}</td><td>{row["seconds"]:.3f}</td><td><pre>{html.escape(row["output"])}</pre></td></tr>')
    body.append('</table>')
    return "\n".join(body) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder")
    p.add_argument("--db", default="runs.db")
    p.add_argument("--html", default="report.html")
    p.add_argument("--timeout", type=float, default=10)
    a = p.parse_args()
    with sqlite3.connect(a.db) as db:
        rows = run_suite(a.folder, db, a.timeout)
    Path(a.html).write_text(render(rows), encoding="utf-8")
    for row in rows:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['bench']}")
    raise SystemExit(1 if any(not row["passed"] for row in rows) else 0)


if __name__ == "__main__":
    main()

