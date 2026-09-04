# Agent Footprint

**See every workspace file a coding-agent command changed — including Git-ignored files, mode bits, and symlink targets.**

Coding-agent UIs can show edits made through their own tools, but terminal commands may write files outside that change list. `git diff` also omits untracked and ignored files. Agent Footprint wraps any command, takes deterministic before/after snapshots, and emits one reviewable Markdown or JSON report. It runs locally, has no runtime dependencies, and never sends file contents anywhere.

## Install

Requires Python 3.10+.

```bash
python3 -m pip install git+https://github.com/Amossse/agent-footprint.git
```

Or clone and install locally:

```bash
git clone https://github.com/Amossse/agent-footprint.git
cd agent-footprint
python3 -m pip install -e .
```

## 5-minute quick start

Run your agent or any shell command after `--`:

```bash
agent-footprint --report footprint.md -- your-agent-command
```

Try a dependency-free example:

```bash
mkdir /tmp/footprint-demo && cd /tmp/footprint-demo
printf 'private.txt\n' > .gitignore
agent-footprint -- python3 -c "from pathlib import Path; Path('private.txt').write_text('created')"
```

The report still includes `private.txt`, even though Git ignores it:

```markdown
- **added** `private.txt` — file, 7 bytes, mode 0644
```

Use JSON in automation, or fail a read-only command that writes anything:

```bash
agent-footprint --json --report footprint.json -- your-agent-command
agent-footprint --fail-on-change -- your-read-only-command  # exits 3 on writes
```

Add `-v` for snapshot diagnostics. Add repeatable `--exclude 'path/**'` patterns for large generated trees. Default noise exclusions are `.git`, `node_modules`, virtual environments, and Python bytecode caches; `--include-noise` disables those defaults.

## What it detects

- Added, modified, and deleted regular files, whether tracked, untracked, or Git-ignored.
- Permission-mode changes such as `0644` → `0755`.
- Symlink creation, deletion, retargeting, and mode changes without following links.
- Special-file metadata changes.

The wrapped command's exit code wins. If the command succeeds, `--fail-on-change` returns 3 when a change is detected. Snapshot or usage errors return 2; a missing command returns 127.

## How it works

Agent Footprint walks the selected root before and after the command, recording path, kind, byte size, permission mode, and SHA-256 digest. It compares those two in-memory maps and renders only metadata—not contents. No daemon, Git integration, database, watcher, or model is involved.

```text
workspace -> snapshot -> command -> snapshot -> deterministic diff -> Markdown/JSON
```

## Limitations

- It reports final state, not transient files created and removed during the command.
- It only observes the selected root. Network, database, cloud, process, and files outside that root are out of scope.
- Empty-directory changes are not reported.
- Concurrent unrelated writes under the root are attributed to the same run.
- Reading and hashing large workspaces costs time and disk I/O; exclude known generated trees when needed.
- It detects changes but does not sandbox, approve, undo, or prove which subprocess performed them.

## Security and privacy

Snapshots and reports stay local. Reports contain paths, sizes, modes, hashes, command arguments, and timestamps, but not file contents. Paths and command arguments can still contain secrets, so review a report before sharing it. The tool executes the command you provide with your current user permissions; it is an observer, not a security boundary. Symlinks are never followed.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the intentionally small contribution scope.

## License

MIT — see [LICENSE](LICENSE).

中文文档：[README.zh-CN.md](README.zh-CN.md)
