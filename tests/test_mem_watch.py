"""tools/mem-watch.sh must stay transparent to the build it wraps.

It wraps ``main.py --all`` in the deploy workflow, so a wrong exit status would
deploy a failed build (or fail a good one), and a warning that never fires would
hide the next out-of-memory approach - the failure it exists to surface.
"""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "mem-watch.sh"

pytestmark = pytest.mark.skipif(not Path("/proc/meminfo").exists(),
                                reason="needs Linux /proc/meminfo")


def _run(*cmd, **env):
    full_env = {**os.environ, "MEM_WATCH_INTERVAL": "0.2", **env}
    full_env.pop("GITHUB_STEP_SUMMARY", None)
    return subprocess.run(["bash", str(SCRIPT), "--", *cmd], env=full_env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("code", [0, 1, 3])
def test_exit_status_is_the_commands(code):
    assert _run("sh", "-c", f"exit {code}").returncode == code


def test_command_output_passes_through():
    out = _run("echo", "hello from the build").stdout
    assert "hello from the build" in out


def test_summary_line_reports_peak_and_exit():
    out = _run("sh", "-c", "sleep 0.5; exit 4").stdout
    line = next(l for l in out.splitlines() if l.startswith("mem-watch: peak"))
    assert "MiB" in line and "exit 4" in line


def test_warning_annotation_fires_over_threshold():
    out = _run("true", MEM_WATCH_WARN_PCT="0").stdout
    assert "::warning title=Build memory::" in out


def test_no_warning_under_threshold():
    out = _run("true", MEM_WATCH_WARN_PCT="101").stdout
    assert "::warning" not in out


def test_progress_lines_at_report_interval():
    out = _run("sleep", "2.5", MEM_WATCH_REPORT="1").stdout
    assert sum(l.startswith("mem-watch: ") and "s used" in l
               for l in out.splitlines()) >= 2


def test_step_summary_is_written(tmp_path):
    summary = tmp_path / "summary.md"
    env = {**os.environ, "MEM_WATCH_INTERVAL": "0.2",
           "GITHUB_STEP_SUMMARY": str(summary)}
    subprocess.run(["bash", str(SCRIPT), "true"], env=env, check=True,
                   capture_output=True, timeout=60)
    assert summary.read_text().startswith("**Build memory:** peak used")


def test_termination_is_passed_to_the_command():
    # A cancelled CI job signals the wrapper; the build must not run on orphaned.
    import signal
    import time
    marker = "37.123"   # a sleep length nothing else on the box uses
    proc = subprocess.Popen(["bash", str(SCRIPT), "--", "sleep", marker],
                            env={**os.environ, "MEM_WATCH_INTERVAL": "0.2"},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)

    def alive():
        return subprocess.run(["pgrep", "-f", f"sleep {marker}"],
                              capture_output=True).returncode == 0
    deadline = time.time() + 5
    while alive() and time.time() < deadline:
        time.sleep(0.1)
    assert not alive()
