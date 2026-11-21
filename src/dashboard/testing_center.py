"""Testing Center tab: run manager unit suites, integration scenarios and
boundary/failure cases, and show pass/fail, expected/actual and diagnostics
(spec section 5).

Suites are groups of test files matched by name, so a new tests/test_parallel_*.py
file shows up under Parallel automatically. The boundary/failure suite runs every
test whose name contains one of BOUNDARY_WORDS.
"""

from pathlib import Path
from typing import List

import streamlit as st

from src.dashboard.test_runner import ROOT, run_tests

TESTS = ROOT / "tests"
RESULTS = "testing-center-results"

SUITES = {
    "Process": ["test_process*.py", "test_validation.py", "test_scenario_builder.py"],
    "Memory": ["test_memory*.py"],
    "File": ["test_file_manager.py", "test_file_view.py"],
    "Security": ["test_security*.py"],
    "Device": ["test_device*.py"],
    "Network": ["test_network*.py"],
    "Parallel": ["test_parallel*.py"],
    "Integration scenarios": ["test_file_memory_integration.py", "test_pipeline.py", "test_controller_api.py",
                              "test_integration*.py"],
    "Dashboard": ["test_app.py", "test_config_sidebar.py", "test_manager_view.py", "test_manager_tab_tools.py",
                  "test_comparison_view.py", "test_overview.py", "test_event_explorer.py", "test_testing_center.py",
                  "test_export.py", "test_process_timeline.py", "test_security_view.py", "test_run_controls.py"],
}
BOUNDARY_SUITE = "Boundary & failure cases"
BOUNDARY_WORDS = ["invalid", "error", "fail", "negative", "duplicate", "missing", "empty", "bad", "denied", "boundary"]


def suite_files(suite: str) -> List[str]:
    if suite == BOUNDARY_SUITE:
        return ["tests"]
    files = {path for pattern in SUITES.get(suite, []) for path in TESTS.glob(pattern)}
    return [str(path.relative_to(ROOT)) for path in sorted(files)]


def run_suite(suite: str):
    keyword = " or ".join(BOUNDARY_WORDS) if suite == BOUNDARY_SUITE else ""
    return run_tests(suite_files(suite), keyword=keyword)


def render_results(suite: str, test_run) -> None:
    if test_run.passed:
        st.success(f"{suite}: {test_run.summary}", icon=":material/check_circle:")
    else:
        st.error(f"{suite}: {test_run.summary}", icon=":material/error:")
    st.dataframe(test_run.results, hide_index=True,
                 column_order=("result", "test", "expected", "actual", "message"))
    with st.expander(f"Diagnostics: full pytest output for {suite}"):
        st.code(test_run.output, language="text")


def render_testing_center() -> None:
    st.subheader("Testing Center")
    st.caption("Runs the automated pytest suites. Failed tests show the expected and actual values from their assertion.")
    suites = [*SUITES, BOUNDARY_SUITE]
    results = st.session_state.setdefault(RESULTS, {})

    if st.button("Run all suites", type="primary", key="testing-run-all"):
        progress = st.progress(0.0, text="Starting...")
        runnable = [s for s in suites if suite_files(s)]
        for index, suite in enumerate(runnable):
            progress.progress(index / len(runnable), text=f"Running {suite} ({index + 1} of {len(runnable)})...")
            results[suite] = run_suite(suite)
        progress.empty()

    columns = st.columns(3)
    for index, suite in enumerate(suites):
        files = suite_files(suite)
        with columns[index % 3].container(border=True):
            st.markdown(f"**{suite}**")
            if suite == BOUNDARY_SUITE:
                st.caption("Tests named with: " + ", ".join(BOUNDARY_WORDS))
            else:
                st.caption(", ".join(Path(f).name for f in files) if files else "No tests yet.")
            if st.button("Run", key=f"testing-run-{suite}", disabled=not files):
                with st.spinner(f"Running {suite}..."):
                    results[suite] = run_suite(suite)

    for suite in suites:
        if suite in results:
            render_results(suite, results[suite])
