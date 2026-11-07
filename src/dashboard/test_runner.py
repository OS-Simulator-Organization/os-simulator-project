"""Runs a manager's pytest files from its dashboard tab (test controls).

Tests run in a separate pytest process so they can't interfere with the
running dashboard. `-rA` makes pytest print one PASSED/FAILED line per test,
which is parsed into a results table.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[2]
RESULT_LINE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)(?: - (.*))?$")


@dataclass(frozen=True)
class TestRun:
    passed: bool
    summary: str
    results: List[Dict[str, str]]
    output: str


def run_tests(files: Sequence[str], timeout_s: int = 300) -> TestRun:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *files, "-q", "-rA", "--tb=short", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout_s,
    )
    output = completed.stdout + completed.stderr
    results = []
    for line in output.splitlines():
        match = RESULT_LINE.match(line.strip())
        if match:
            outcome, test, message = match.groups()
            results.append({"test": test, "result": outcome, "message": message or ""})
    lines = [line for line in output.splitlines() if line.strip()]
    summary = lines[-1].strip("= ") if lines else "No output from pytest."
    return TestRun(completed.returncode == 0, summary, results, output)
