"""Loop-guard hook behaviour, exercised as a subprocess the way Claude Code runs it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "loop_guard.py"


def run_hook(
    mode: str, event: dict[str, Any] | str, project_dir: Path, **env: str
) -> subprocess.CompletedProcess[str]:
    payload = event if isinstance(event, str) else json.dumps({"session_id": "s1", **event})
    return subprocess.run(
        [sys.executable, str(HOOK), mode],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), **env},
        timeout=10,
        check=False,
    )


def bash(command: str, **extra: Any) -> dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": command}, **extra}


def edit(old: str, new: str, path: str = "src/x.py") -> dict[str, Any]:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": path, "old_string": old, "new_string": new},
    }


def run_failing(project: Path, command: str, stderr: str) -> None:
    assert run_hook("pre", bash(command), project).returncode == 0
    response = {"stdout": "", "stderr": stderr}
    assert run_hook("post", bash(command, tool_response=response), project).returncode == 0


def test_unrelated_tool_is_allowed(tmp_path: Path) -> None:
    result = run_hook("pre", {"tool_name": "Read", "tool_input": {"file_path": "a"}}, tmp_path)
    assert result.returncode == 0


def test_same_result_three_times_blocks_next_run_once(tmp_path: Path) -> None:
    for attempt in range(3):
        # durations differ between runs; digits are normalised away
        run_failing(tmp_path, "make test", f"FAILED tests/test_a.py::test_x in 0.{attempt}5s")
    blocked = run_hook("pre", bash("make test"), tmp_path)
    assert blocked.returncode == 2
    assert "loop-guard" in blocked.stderr
    assert run_hook("pre", bash("make test"), tmp_path).returncode == 0


def test_changing_results_never_block(tmp_path: Path) -> None:
    for name in ("test_a", "test_b", "test_c", "test_d"):
        run_failing(tmp_path, "make test", f"FAILED {name}")
    assert run_hook("pre", bash("make test"), tmp_path).returncode == 0


def test_read_only_commands_are_exempt(tmp_path: Path) -> None:
    for _ in range(4):
        run_failing(tmp_path, "git status", "nothing to commit")
    assert run_hook("pre", bash("git status"), tmp_path).returncode == 0


def test_single_revert_is_allowed_but_reapplying_it_is_blocked(tmp_path: Path) -> None:
    assert run_hook("pre", edit("a = 1", "a = 2"), tmp_path).returncode == 0
    assert run_hook("pre", edit("a = 2", "a = 1"), tmp_path).returncode == 0
    blocked = run_hook("pre", edit("a = 1", "a = 2"), tmp_path)
    assert blocked.returncode == 2
    assert "src/x.py" in blocked.stderr


def test_multiedit_oscillation_is_detected(tmp_path: Path) -> None:
    def multi(old: str, new: str) -> dict[str, Any]:
        edits = [{"old_string": old, "new_string": new}]
        return {"tool_name": "MultiEdit", "tool_input": {"file_path": "f.py", "edits": edits}}

    assert run_hook("pre", multi("x", "y"), tmp_path).returncode == 0
    assert run_hook("pre", multi("y", "x"), tmp_path).returncode == 0
    assert run_hook("pre", multi("x", "y"), tmp_path).returncode == 2


def test_call_cap_blocks_one_call_and_then_allows(tmp_path: Path) -> None:
    codes = [
        run_hook("pre", bash(f"echo {i}"), tmp_path, LOOP_GUARD_MAX_CALLS="3").returncode
        for i in range(4)
    ]
    assert codes == [0, 0, 2, 0]


def test_sessions_do_not_share_state(tmp_path: Path) -> None:
    for _ in range(3):
        run_failing(tmp_path, "make test", "FAILED test_a")
    other = json.dumps({"session_id": "s2", **bash("make test")})
    assert run_hook("pre", other, tmp_path).returncode == 0
    assert (tmp_path / ".claude" / "state" / "loop_guard" / "s1.json").is_file()


@pytest.mark.parametrize("payload", ["not json", "[1, 2]", ""])
def test_malformed_input_fails_open(tmp_path: Path, payload: str) -> None:
    assert run_hook("pre", payload, tmp_path).returncode == 0


def test_unknown_mode_is_ignored(tmp_path: Path) -> None:
    assert run_hook("weird", bash("make test"), tmp_path).returncode == 0
