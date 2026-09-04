# Agent Footprint

**看清编码 Agent 的终端命令改了哪些工作区文件——包括 Git 忽略文件、权限位和符号链接目标。**

编码 Agent 的界面通常能展示自身编辑工具产生的改动，但终端命令写入的文件可能不在变更列表里；`git diff` 也不会展示未跟踪与被忽略文件。Agent Footprint 包裹任意命令，在运行前后做确定性快照，并输出一份可审查的 Markdown 或 JSON 报告。它完全本地运行、无运行时依赖，也不会上传文件内容。

## 安装

需要 Python 3.10+。

```bash
python3 -m pip install git+https://github.com/Amossse/agent-footprint.git
```

或克隆后本地安装：

```bash
git clone https://github.com/Amossse/agent-footprint.git
cd agent-footprint
python3 -m pip install -e .
```

## 5 分钟快速开始

在 `--` 后放入 Agent 或任意命令：

```bash
agent-footprint --report footprint.md -- your-agent-command
```

用零依赖示例验证：

```bash
mkdir /tmp/footprint-demo && cd /tmp/footprint-demo
printf 'private.txt\n' > .gitignore
agent-footprint -- python3 -c "from pathlib import Path; Path('private.txt').write_text('created')"
```

即使 Git 忽略 `private.txt`，报告仍会显示：

```markdown
- **added** `private.txt` — file, 7 bytes, mode 0644
```

自动化场景可输出 JSON；对于本应只读的命令，可在发生写入时失败：

```bash
agent-footprint --json --report footprint.json -- your-agent-command
agent-footprint --fail-on-change -- your-read-only-command  # 检测到写入时退出码为 3
```

使用 `-v` 输出快照诊断日志；可重复传入 `--exclude 'path/**'` 排除大型生成目录。默认跳过 `.git`、`node_modules`、虚拟环境和 Python 字节码缓存；`--include-noise` 可关闭这些默认排除项。

## 能检测什么

- 普通文件的新增、修改和删除，包括已跟踪、未跟踪及 Git 忽略文件。
- `0644` → `0755` 之类的权限变化。
- 符号链接的新建、删除、改指向及权限变化，且不会跟随链接。
- 特殊文件的元数据变化。

被包裹命令的退出码优先返回。命令成功时，`--fail-on-change` 在发现改动后返回 3；快照或参数错误返回 2；命令不存在返回 127。

## 实现方式

工具在命令运行前后遍历指定根目录，记录路径、类型、字节数、权限模式与 SHA-256 摘要，在内存中比较两个映射，只输出元数据而非文件内容。不需要守护进程、Git 集成、数据库、文件监听器或模型。

```text
工作区 -> 前快照 -> 执行命令 -> 后快照 -> 确定性差异 -> Markdown/JSON
```

## 已知限制

- 只报告最终状态，无法发现命令运行中创建后又删除的临时文件。
- 只观察指定根目录；网络、数据库、云端、进程及目录外文件不在范围内。
- 不报告空目录变化。
- 并发发生的其他写入也会归入同一次报告。
- 大型工作区的读取与哈希会产生时间和磁盘 I/O 开销，可排除已知生成目录。
- 工具只检测，不提供沙箱、审批、撤销，也不能证明具体由哪个子进程完成写入。

## 安全与隐私

快照和报告只保留在本机。报告包含路径、大小、权限、哈希、命令参数与时间戳，但不包含文件内容。路径或命令参数本身仍可能携带秘密，分享报告前请检查。工具以当前用户权限直接执行你提供的命令，因此它是观察器，不是安全边界。符号链接永不跟随。

## 开发

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

贡献范围见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT，见 [LICENSE](LICENSE)。

English: [README.md](README.md)
