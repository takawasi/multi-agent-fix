"""Tests for test runner."""

from multi_agent_fix.runner import parse_failed_tests, detect_test_framework
from pathlib import Path
import tempfile


def test_parse_pytest_failures():
    """Parse pytest failure output."""
    output = """
FAILED tests/test_foo.py::test_bar - AssertionError
FAILED tests/test_baz.py::test_qux - ValueError
PASSED tests/test_other.py::test_ok
"""
    failed = parse_failed_tests(output, "pytest")
    assert len(failed) == 2
    assert "tests/test_foo.py::test_bar" in failed
    assert "tests/test_baz.py::test_qux" in failed


def test_parse_go_failures():
    """Parse go test failure output."""
    output = """
--- FAIL: TestSomething (0.01s)
--- FAIL: TestAnother (0.02s)
PASS
"""
    failed = parse_failed_tests(output, "go")
    assert len(failed) == 2


def test_detect_pytest():
    """Detect pytest framework."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "pytest.ini").touch()
        assert detect_test_framework(path) == "pytest"


def test_detect_npm():
    """Detect npm framework."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "package.json").touch()
        assert detect_test_framework(path) == "npm"
