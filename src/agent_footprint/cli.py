from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import logging
import os
import shlex
import stat
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

LOG = logging.getLogger("agent-footprint")

DEFAULT_EXCLUDES = (
    ".git",
    ".git/**",
    "node_modules",
    "**/node_modules",
    "**/node_modules/**",
    ".venv",
    ".venv/**",
    "**/.venv",
    "**/.venv/**",
    "venv",
    "venv/**",
    "**/venv",
    "**/venv/**",
    "__pycache__",
    "**/__pycache__",
    "**/__pycache__/**",
)


class FootprintError(RuntimeError):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str
    size: int
    mode: str
    digest: str


@dataclass(frozen=True)
class Change:
    path: str
    status: str
    before: Entry | None
    after: Entry | None


def _excluded(relative: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns)


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise FootprintError(f"cannot read {path}: {error}") from error
    return digest.hexdigest()


def _entry(path: Path) -> Entry:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise FootprintError(f"cannot stat {path}: {error}") from error

    mode = f"{stat.S_IMODE(metadata.st_mode):04o}"
    if stat.S_ISLNK(metadata.st_mode):
        try:
            target = os.readlink(path)
        except OSError as error:
            raise FootprintError(f"cannot read symlink {path}: {error}") from error
        return Entry(
            "symlink",
            len(target.encode()),
            mode,
            hashlib.sha256(target.encode()).hexdigest(),
        )
    if stat.S_ISREG(metadata.st_mode):
        return Entry("file", metadata.st_size, mode, _digest_file(path))
    return Entry("special", metadata.st_size, mode, "")


def snapshot(root: Path, excludes: Sequence[str]) -> dict[str, Entry]:
    result: dict[str, Entry] = {}

    def visit(directory: Path) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise FootprintError(f"cannot scan {directory}: {error}") from error
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(root).as_posix()
            if _excluded(relative, excludes):
                continue
            try:
                if child.is_dir(follow_symlinks=False):
                    visit(path)
                else:
                    result[relative] = _entry(path)
            except OSError as error:
                raise FootprintError(f"cannot inspect {path}: {error}") from error

    LOG.info("snapshot start root=%s", root)
    visit(root)
    LOG.info("snapshot complete root=%s entries=%d", root, len(result))
    return result


def compare(before: dict[str, Entry], after: dict[str, Entry]) -> list[Change]:
    changes: list[Change] = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        status = "added" if old is None else "deleted" if new is None else "modified"
        changes.append(Change(path, status, old, new))
    return changes


def _change_reason(change: Change) -> str:
    if change.before is None:
        assert change.after is not None
        return (
            f"{change.after.kind}, {change.after.size} bytes, mode {change.after.mode}"
        )
    if change.after is None:
        return f"was {change.before.kind}, {change.before.size} bytes, mode {change.before.mode}"
    differences = []
    if change.before.kind != change.after.kind:
        differences.append(f"kind {change.before.kind}->{change.after.kind}")
    if change.before.size != change.after.size:
        differences.append(f"size {change.before.size}->{change.after.size}")
    if change.before.mode != change.after.mode:
        differences.append(f"mode {change.before.mode}->{change.after.mode}")
    if change.before.digest != change.after.digest:
        differences.append("content/target changed")
    return ", ".join(differences)


def _json_report(report: dict[str, object]) -> str:
    return json.dumps(report, default=asdict, ensure_ascii=False, indent=2) + "\n"


def _inline_code(value: object) -> str:
    visible = str(value).replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return f"<code>{html.escape(visible, quote=False)}</code>"


def _markdown_report(report: dict[str, object], changes: Iterable[Change]) -> str:
    command = shlex.join(cast(list[str], report["command"]))
    exit_code = report["exit_code"] if report["exit_code"] is not None else "pending"
    finished = report["finished_at"] if report["finished_at"] is not None else "pending"
    lines = [
        "# Agent Footprint Report",
        "",
        f"- Status: {report.get('status', 'completed')}",
        f"- Command: {_inline_code(command)}",
        f"- Root: {_inline_code(report['root'])}",
        f"- Exit code: {exit_code}",
        f"- Started: {report['started_at']}",
        f"- Finished: {finished}",
        f"- Changes: {report['change_count']}",
        "",
        "## Filesystem changes",
        "",
    ]
    rendered = list(changes)
    if not rendered:
        lines.append("No changes detected.")
    else:
        for change in rendered:
            lines.append(
                f"- **{change.status}** {_inline_code(change.path)} — {_change_reason(change)}"
            )
    return "\n".join(lines) + "\n"


def _report(
    root: Path,
    command: list[str],
    started: str,
    before: dict[str, Entry],
    after: dict[str, Entry],
    status: str,
    exit_code: int | None,
) -> tuple[dict[str, object], list[Change]]:
    changes = compare(before, after)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "status": status,
        "root": str(root),
        "command": command,
        "exit_code": exit_code,
        "started_at": started,
        "checked_at": now,
        "finished_at": now if status == "completed" else None,
        "change_count": len(changes),
        "changes": changes,
    }, changes


def _write_report(path: Path, output: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(output, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as error:
        raise FootprintError(f"cannot write report {path}: {error}") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-footprint",
        description="Run a command and report every workspace file, mode, and symlink change.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="workspace to snapshot (default: cwd)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="extra relative glob to skip",
    )
    parser.add_argument(
        "--include-noise",
        action="store_true",
        help="also scan .git, dependencies, and caches",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit JSON instead of Markdown"
    )
    parser.add_argument(
        "--report", type=Path, help="write the report to a file instead of stdout"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="refresh --report while the command is still running",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="live snapshot interval (default: 1.0)",
    )
    parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="exit 3 when the command succeeds but changes files",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="log snapshot progress to stderr"
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="command after --")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a command is required after --")
    if args.live and args.report is None:
        parser.error("--live requires --report")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    root = args.root.resolve()
    if not root.is_dir():
        print(f"agent-footprint: root is not a directory: {root}", file=sys.stderr)
        return 2
    excludes = (
        tuple(args.exclude)
        if args.include_noise
        else DEFAULT_EXCLUDES + tuple(args.exclude)
    )
    report_path = args.report.resolve() if args.report else None
    if args.live and report_path:
        # Live output must not report its own atomic writes as workspace changes.
        for generated in (
            report_path,
            report_path.with_name(f".{report_path.name}.tmp"),
        ):
            try:
                excludes += (generated.relative_to(root).as_posix(),)
            except ValueError:
                pass

    try:
        before = snapshot(root, excludes)
        started = datetime.now(timezone.utc).isoformat()
        try:
            if args.live:
                process = subprocess.Popen(command, cwd=root)
                live_report, live_changes = _report(
                    root, command, started, before, before, "running", None
                )
                assert report_path is not None
                _write_report(
                    report_path,
                    _json_report(live_report)
                    if args.json
                    else _markdown_report(live_report, live_changes),
                )
                last_changes = live_changes
                # ponytail: polling stays dependency-free; use native file events if large repos need it.
                while True:
                    try:
                        return_code = process.wait(timeout=args.interval)
                        break
                    except subprocess.TimeoutExpired:
                        current = snapshot(root, excludes)
                        live_report, live_changes = _report(
                            root, command, started, before, current, "running", None
                        )
                        if live_changes != last_changes:
                            _write_report(
                                report_path,
                                _json_report(live_report)
                                if args.json
                                else _markdown_report(live_report, live_changes),
                            )
                            last_changes = live_changes
                exit_code = return_code if return_code >= 0 else 128 - return_code
            else:
                completed = subprocess.run(command, cwd=root, check=False)
                exit_code = (
                    completed.returncode
                    if completed.returncode >= 0
                    else 128 - completed.returncode
                )
        except FileNotFoundError:
            print(f"agent-footprint: command not found: {command[0]}", file=sys.stderr)
            exit_code = 127
        except KeyboardInterrupt:
            exit_code = 130
        after = snapshot(root, excludes)
    except FootprintError as error:
        print(f"agent-footprint: {error}", file=sys.stderr)
        return 2

    report, changes = _report(
        root, command, started, before, after, "completed", exit_code
    )
    output = _json_report(report) if args.json else _markdown_report(report, changes)
    if report_path:
        try:
            _write_report(report_path, output)
        except FootprintError as error:
            print(f"agent-footprint: {error}", file=sys.stderr)
            return 2
        LOG.info("report written path=%s", report_path)
    else:
        print(output, end="")

    if exit_code:
        return exit_code
    return 3 if args.fail_on_change and changes else 0
