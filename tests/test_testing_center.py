from src.dashboard.test_runner import run_tests, split_assertion
from src.dashboard.testing_center import BOUNDARY_SUITE, suite_files

FIXTURE = '''
def test_passes():
    assert 1 + 1 == 2

def test_wrong_total_fails():
    total = 3
    assert total == 4

def test_negative_value_is_rejected():
    assert -1 < 0
'''


def test_split_assertion_reads_expected_and_actual():
    assert split_assertion("assert 3 == 4") == ("4", "3")
    assert split_assertion("ValueError: boom") == ("", "")


def test_run_tests_reports_expected_and_actual_for_failures(tmp_path):
    fixture = tmp_path / "test_fixture.py"
    fixture.write_text(FIXTURE)
    results = {r["test"].split("::")[-1]: r for r in run_tests([str(fixture)]).results}
    assert results["test_passes"]["result"] == "PASSED"
    assert (results["test_wrong_total_fails"]["expected"], results["test_wrong_total_fails"]["actual"]) == ("4", "3")


def test_keyword_runs_only_matching_tests(tmp_path):
    fixture = tmp_path / "test_fixture.py"
    fixture.write_text(FIXTURE)
    names = [r["test"].split("::")[-1] for r in run_tests([str(fixture)], keyword="negative").results]
    assert names == ["test_negative_value_is_rejected"]


def test_suites_are_matched_by_file_name():
    assert any(f.endswith("test_validation.py") for f in suite_files("Process"))
    assert any(f.endswith("test_security_manager.py") for f in suite_files("Security"))
    assert suite_files("Parallel") == []
    assert suite_files(BOUNDARY_SUITE) == ["tests"]
