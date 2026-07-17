#!/usr/bin/env python3
"""tmux-backed client for a raw TCP MUD session.

A MUD connection is stateful and long-lived, but every Claude tool call is a
fresh subprocess. tmux solves that mismatch: `nc` runs inside a detached
tmux session that keeps living between tool calls, and this script just
sends keystrokes into it and reads back whatever new text appeared.

Usage:
    mud_client.py start                  # open the connection (idempotent)
    mud_client.py send "<command>"       # send one line, print the new output
    mud_client.py status                 # "running" or "stopped"
    mud_client.py stop                   # close the connection
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

SESSION = "mud"
HOST = "localhost"
PORT = "4000"
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "session_state.json"

# nc has no telnet IAC negotiation, so stray negotiation bytes reach the
# terminal. tmux renders them as U+FFFD; strip anything non-printable that
# survives capture-pane's own ANSI/color handling.
JUNK_RE = re.compile(r'[�\x00-\x08\x0b\x0c\x0e-\x1f]')


def session_exists() -> bool:
    return subprocess.run(["tmux", "has-session", "-t", SESSION],
                           capture_output=True).returncode == 0


def capture_lines() -> list[str]:
    # capture-pane always pads its output to the full pane height with blank
    # lines below the cursor, so a fixed-size grid doesn't mean fixed content.
    # Trim that trailing padding so line counts reflect real output growth.
    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", SESSION, "-S", "-100000"],
        capture_output=True, text=True)
    lines = [JUNK_RE.sub('', line) for line in result.stdout.splitlines()]
    while lines and lines[-1] == '':
        lines.pop()
    return lines


def save_state(line_count: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"line_count": line_count}))


def load_state() -> int:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("line_count", 0)
    return 0


def start() -> None:
    if session_exists():
        print("Session already running.")
        return
    subprocess.run(["tmux", "new-session", "-d", "-s", SESSION, "-x", "220", "-y", "50"])
    subprocess.run(["tmux", "set-option", "-t", SESSION, "history-limit", "100000"])
    subprocess.run(["tmux", "send-keys", "-t", SESSION, f"nc {HOST} {PORT}", "Enter"])
    time.sleep(1.5)
    lines = capture_lines()
    save_state(len(lines))
    print("\n".join(lines))


def send(text: str, wait: float) -> None:
    if not session_exists():
        print("ERROR: no active session. Run 'start' first.", file=sys.stderr)
        sys.exit(1)
    pre = load_state()
    subprocess.run(["tmux", "send-keys", "-t", SESSION, text, "Enter"])
    time.sleep(wait)
    lines = capture_lines()
    save_state(len(lines))
    new_lines = lines[pre:] if len(lines) > pre else lines[-5:]
    print("\n".join(new_lines))


def status() -> None:
    print("running" if session_exists() else "stopped")


def stop() -> None:
    if session_exists():
        subprocess.run(["tmux", "kill-session", "-t", SESSION])
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start")
    sub.add_parser("status")
    sub.add_parser("stop")
    p_send = sub.add_parser("send")
    p_send.add_argument("text")
    p_send.add_argument("--wait", type=float, default=0.8,
                         help="seconds to wait for the server to respond before reading")
    args = parser.parse_args()

    {
        "start": start,
        "status": status,
        "stop": stop,
        "send": lambda: send(args.text, args.wait),
    }[args.cmd]()


if __name__ == "__main__":
    main()
