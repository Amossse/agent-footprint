# Launch copy

## English

Coding-agent UIs can miss files changed through terminal commands, while `git diff` misses ignored files. I built **Agent Footprint**, a zero-dependency local CLI that wraps any command and reports added, modified, deleted, permission, and symlink changes as Markdown or JSON—even while an interactive agent is still running. No daemon, no model, no file contents uploaded. Try it in five minutes: `agent-footprint --live --report footprint.md -- codex`.

## 中文

编码 Agent 的界面可能漏掉终端命令写入的文件，`git diff` 又看不到被忽略文件。我做了 **Agent Footprint**：一个零运行时依赖、本地运行的命令行工具，包裹任意 Agent 或脚本，即使交互式 Agent 仍在运行，也会持续输出新增、修改、删除、权限位和符号链接变化，支持 Markdown/JSON。无需守护进程、无需模型，也不上传文件内容。五分钟试用：`agent-footprint --live --report footprint.md -- codex`。

## Repository metadata

- Title: Agent Footprint — reveal the files terminal-driven coding agents changed
- Description: Reveal filesystem changes that coding-agent terminal commands leave behind, including ignored files, modes, and symlinks.
- Suggested topics: `ai-agents`, `audit`, `cli`, `coding-agents`, `developer-tools`, `filesystem`, `python`
