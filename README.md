# HDL Regression Test Runner

Discover `*_tb.v` benches, compile each with Icarus Verilog, run it with `vvp`, enforce a timeout, and store results in SQLite. The generated HTML report shows elapsed time and captured output for each bench.

```sh
python runner.py examples --db runs.db --html report.html --timeout 10
python -m unittest discover -s tests -v
```

The simulator commands must be on `PATH` for the CLI. A bench passes only when the process exits successfully and emits a standalone `PASS`; `FAIL:` lines always fail. Unit tests use a fake command runner so parser and failure paths are reproducible without a simulator. `mutate_operator()` can create a one-operator mutant for checking whether a bench catches that change.

