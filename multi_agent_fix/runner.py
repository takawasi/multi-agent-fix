"""Test runner and failure detection."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    """Result of running tests."""

    passed: bool
    output: str
    failed_tests: list[str]


@dataclass
class FailedTest:
    """Information about a failed test."""

    name: str
    file: str
    error: str
    source: str


def detect_test_framework(path: Path) -> str:
    """Detect the test framework used in the project."""
    if (path / "pytest.ini").exists() or (path / "pyproject.toml").exists():
        return "pytest"
    if (path / "package.json").exists():
        return "npm"
    if (path / "Cargo.toml").exists():
        return "cargo"
    if (path / "go.mod").exists():
        return "go"
    return "pytest"  # default


def run_tests(path: Path, framework: str) -> TestResult:
    """Run tests and return results."""
    commands = {
        "pytest": ["python", "-m", "pytest", "-v", "--tb=short"],
        "npm": ["npm", "test"],
        "cargo": ["cargo", "test"],
        "go": ["go", "test", "./..."],
    }

    cmd = commands.get(framework, commands["pytest"])

    try:
        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        failed_tests = parse_failed_tests(output, framework)
        return TestResult(passed=passed, output=output, failed_tests=failed_tests)
    except subprocess.TimeoutExpired:
        return TestResult(passed=False, output="Test timeout", failed_tests=[])
    except Exception as e:
        return TestResult(passed=False, output=str(e), failed_tests=[])


def parse_failed_tests(output: str, framework: str) -> list[str]:
    """Parse test output to find failed test names."""
    failed = []

    if framework == "pytest":
        for line in output.split("\n"):
            if "FAILED" in line and "::" in line:
                # Format: FAILED tests/test_foo.py::test_bar
                parts = line.split("FAILED")[1].strip()
                if parts:
                    failed.append(parts.split()[0])

    elif framework == "npm":
        for line in output.split("\n"):
            if "✕" in line or "FAIL" in line:
                failed.append(line.strip())

    elif framework == "cargo":
        for line in output.split("\n"):
            if "FAILED" in line or "test result:" in line:
                failed.append(line.strip())

    elif framework == "go":
        for line in output.split("\n"):
            if "--- FAIL:" in line:
                failed.append(line.replace("--- FAIL:", "").strip())

    return failed


def get_test_context(path: Path, test_name: str, framework: str) -> FailedTest:
    """Get the source code context for a failed test."""
    if framework == "pytest" and "::" in test_name:
        file_part = test_name.split("::")[0]
        test_file = path / file_part
        if test_file.exists():
            source = test_file.read_text()
            return FailedTest(
                name=test_name,
                file=str(test_file),
                error="",
                source=source,
            )

    return FailedTest(name=test_name, file="", error="", source="")


def apply_fix(path: Path, file: str, new_content: str) -> bool:
    """Apply a fix to a file."""
    try:
        file_path = Path(file)
        if not file_path.is_absolute():
            file_path = path / file
        file_path.write_text(new_content)
        return True
    except Exception:
        return False
