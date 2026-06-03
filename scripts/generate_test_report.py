import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "tests" / "report"


def run_command(command):
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:tests/report/coverage_html",
        "--cov-report=json:tests/report/coverage.json",
    ]
    result = run_command(command)
    (REPORT_DIR / "pytest_output.txt").write_text(result.stdout, encoding="utf-8")

    coverage_percent = "unknown"
    coverage_json = REPORT_DIR / "coverage.json"
    if coverage_json.exists():
        data = json.loads(coverage_json.read_text(encoding="utf-8"))
        coverage_percent = data.get("totals", {}).get("percent_covered_display", "unknown")

    summary = [
        "# CryptoSafe Manager Test Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Exit code: {result.returncode}",
        f"Coverage: {coverage_percent}%",
        "",
        "## Command",
        "",
        "```text",
        " ".join(command),
        "```",
        "",
        "## Pytest Output",
        "",
        "```text",
        result.stdout,
        "```",
    ]
    (REPORT_DIR / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
