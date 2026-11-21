"""Runs a manager's pytest files from its dashboard tab (test controls).

Tests run in a separate pytest process so they can't interfere with the
running dashboard. `-rA` makes pytest print one PASSED/FAILED line per test,
which is parsed into a results table.
"""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
# Test names can contain spaces (parametrized ids), so the name runs up to " - " or the end of the line.
RESULT_LINE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (.+?)(?: - (.*))?$")
ASSERT_EQUAL = re.compile(r"assert (.+?) == (.+)")


@dataclass(frozen=True)
class TestRun:
    passed: bool
    summary: str
    results: List[Dict[str, str]]
    output: str


def split_assertion(message: str) -> Tuple[str, str]:
    """Reads (expected, actual) from pytest's "assert actual == expected" failure message."""
    match = ASSERT_EQUAL.search(message)
    return (match.group(2).strip(), match.group(1).strip()) if match else ("", "")


def run_tests(files: Sequence[str], keyword: str = "", timeout_s: int = 300) -> TestRun:
    """Runs the given test files. `keyword` is passed to pytest -k to run only matching tests."""
    command = [sys.executable, "-m", "pytest", *files, "-q", "-rA", "--tb=short", "-p", "no:cacheprovider"]
    if keyword:
        command += ["-k", keyword]
    # A wide terminal keeps pytest from cutting the failure message off the end of each FAILED line.
    environment = {**os.environ, "COLUMNS": "1000"}
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout_s, env=environment)
    output = completed.stdout + completed.stderr
    results = []
    for line in output.splitlines():
        match = RESULT_LINE.match(line.strip())
        if match:
            outcome, test, message = match.groups()
            expected, actual = split_assertion(message or "")
            results.append({"test": test, "result": outcome, "expected": expected, "actual": actual,
                            "message": message or ""})
    lines = [line for line in output.splitlines() if line.strip()]
    summary = lines[-1].strip("= ") if lines else "No output from pytest."
    return TestRun(completed.returncode == 0, summary, results, output)
