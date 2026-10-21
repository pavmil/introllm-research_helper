#!/usr/bin/env python3
"""Claude Code hook that stops the development agent from looping (ADR-0002, AGENTS.md §6).

Wired in .claude/settings.json:

* PreToolUse  (Bash|Edit|MultiEdit|Write)          -> ``loop_guard.py pre``
* PostToolUse and PostToolUseFailure (Bash)        -> ``loop_guard.py post``

Rules (exit code 2 blocks the tool call; stderr is shown to the agent):

1. The same Bash command gave the same result LOOP_GUARD_MAX_SAME_RESULT times in a row
   (default 3; digits are ignored, so test durations do not hide a repeat): the next run of
   that command is blocked once. Read-only commands (git status/diff/log, ls, cat...) are exempt.
2. An Edit re-applies a change the agent has already reverted (A->B, B->A, A->B): blocked.
   A single revert (e.g. removing a debug print) is allowed.
3. Every LOOP_GUARD_MAX_CALLS tool calls (default 300): one call is blocked with a request
   to stop and report progress to the human.

The hook must never break a session: on any internal error it exits 0 (fails open).
State: .claude/state/loop_guard/<session_id>.json (gitignored).
Runs on the system python3 (3.9 on macOS): standard library and pre-3.10 syntax only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BLOCK_EXIT_CODE = 2
DEFAULT_MAX_SAME_RESULT = 3
DEFAULT_MAX_CALLS = 300
RESULTS_KEPT = 10
READ_ONLY_COMMAND = re.compile(
    r"^\s*(git\s+(status|diff|log|show|branch)|ls|pwd|cat|head|tail|wc|echo|which)\b"
)
DIGITS = re.compile(r"\d+(\.\d+)?")

State = dict[str, Any]


def _digest(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _state_path(session_id: str) -> Path:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_") or "unknown"
    return root / ".claude" / "state" / "loop_guard" / f"{safe}.json"


def _load(path: Path) -> State:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("calls", 0)
    state.setdefault("bash", {})
    state.setdefault("edits", {})
    return state


def _save(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(path)


def _command(tool_input: dict[str, Any]) -> str:
    return " ".join(str(tool_input.get("command", "")).split())


def _outcome_digest(event: dict[str, Any]) -> str:
    outcome = event.get("tool_response")
    if outcome is None:
        outcome = event.get("error")
    text = json.dumps(outcome, sort_keys=True, ensure_ascii=False, default=str)
    return _digest(DIGITS.sub("N", text))


def _edit_triples(tool_name: str, tool_input: dict[str, Any]) -> list[tuple[str, str, str]]:
    file_path = str(tool_input.get("file_path", ""))
    edits = tool_input.get("edits") if tool_name == "MultiEdit" else [tool_input]
    if not isinstance(edits, list):
        return []
    return [
        (file_path, str(edit.get("old_string", "")), str(edit.get("new_string", "")))
        for edit in edits
        if isinstance(edit, dict)
    ]


def _check_repeated_result(tool_input: dict[str, Any], state: State) -> str | None:
    command = _command(tool_input)
    if READ_ONLY_COMMAND.match(command):
        return None
    key = _digest(command)
    results = state["bash"].get(key, [])
    limit = _env_int("LOOP_GUARD_MAX_SAME_RESULT", DEFAULT_MAX_SAME_RESULT)
    if len(results) >= limit and len(set(results[-limit:])) == 1:
        state["bash"][key] = []
        return (
            f"loop-guard: команда `{command[:120]}` {limit} раза подряд дала одинаковый "
            "результат — повтор ничего не изменит. Правило трёх попыток (AGENTS.md §6): "
            "запиши в журнал задачи, что пробовал, смени гипотезу или спроси человека. "
            "Не обходи блок переформулировкой той же команды."
        )
    return None


def _check_edit_oscillation(tool_name: str, tool_input: dict[str, Any], state: State) -> str | None:
    triples = _edit_triples(tool_name, tool_input)
    edits: dict[str, int] = state["edits"]
    for file_path, old, new in triples:
        forward = _digest([file_path, old, new])
        reverse = _digest([file_path, new, old])
        if edits.get(forward, 0) >= 1 and edits.get(reverse, 0) >= 1:
            return (
                f"loop-guard: правка в {file_path} повторяет изменение, которое уже было "
                "откатано (A→B→A→B). Это зацикливание (AGENTS.md §6): остановись, запиши "
                "гипотезы в журнал задачи и выбери одно решение или спроси человека."
            )
    for file_path, old, new in triples:
        forward = _digest([file_path, old, new])
        edits[forward] = edits.get(forward, 0) + 1
    return None


def handle_pre(event: dict[str, Any], state: State) -> str | None:
    """Return a block message, or None to allow the tool call."""
    state["calls"] += 1
    max_calls = _env_int("LOOP_GUARD_MAX_CALLS", DEFAULT_MAX_CALLS)
    if state["calls"] % max_calls == 0:
        return (
            f"loop-guard: в этой сессии уже {state['calls']} вызовов инструментов. "
            "Остановись и кратко отчитайся человеку: что сделано, что осталось, нет ли "
            "зацикливания (AGENTS.md §6). Следующий вызов будет разрешён."
        )
    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    if tool_name == "Bash":
        return _check_repeated_result(tool_input, state)
    if tool_name in ("Edit", "MultiEdit"):
        return _check_edit_oscillation(tool_name, tool_input, state)
    return None


def handle_post(event: dict[str, Any], state: State) -> None:
    """Remember the (digit-normalised) result of a Bash command."""
    tool_input = event.get("tool_input")
    if event.get("tool_name") != "Bash" or not isinstance(tool_input, dict):
        return
    command = _command(tool_input)
    if READ_ONLY_COMMAND.match(command):
        return
    results: list[str] = state["bash"].setdefault(_digest(command), [])
    results.append(_outcome_digest(event))
    del results[:-RESULTS_KEPT]


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    message: str | None = None
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict) or mode not in ("pre", "post"):
            return 0
        path = _state_path(str(event.get("session_id") or "unknown"))
        state = _load(path)
        if mode == "pre":
            message = handle_pre(event, state)
        else:
            handle_post(event, state)
        _save(path, state)
    except Exception as exc:  # noqa: BLE001 — the hook must never break the session
        sys.stderr.write(f"loop-guard: internal error ignored: {exc}\n")
        return 0
    if message:
        sys.stderr.write(message + "\n")
        return BLOCK_EXIT_CODE
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
