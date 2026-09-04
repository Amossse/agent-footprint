# Research record — 2026-09-04

Window: 2026-08-29 through 2026-09-04. Checked official announcements, recent paper/model activity, current GitHub Trending, and nearby open-source tools.

## Evidence

- [Visual Studio Code: Review and revert agent changes](https://code.visualstudio.com/docs/agents/run/review-code-edits), updated 2026-09-02, says its changed-files list includes file-edit-tool changes but not files only changed through terminal commands. This is the direct product gap.
- [GitHub Trending](https://github.com/trending), checked 2026-09-04, was dominated by agent tooling: OpenMAIC gained 3,128 stars that day; academic-research-skills gained 193; scientific-agent-skills gained 912. More agent-executed workflows increase the value of a vendor-neutral audit seam.
- [OpenAI: Path to Astra](https://openai.com/index/path-to-astra/), published 2026-09-01, describes stronger monitoring and the possibility that long-running agent tasks are paused or stopped. That raises the value of inspectable state left by interrupted runs, though Agent Footprint does not monitor model behavior.
- [NeoMME](https://huggingface.co/blog/Hcompany/neomme), published 2026-09-03, released efficient multimodal retrieval models and demonstrated strong current interest in visual RAG. A visual-RAG helper was rejected because the useful version would require model/runtime dependencies and duplicate existing PDF-routing tools.
- [What Keeps Agent Skills from Being Reusable?](https://arxiv.org/abs/2608.08453), published in August 2026, studies 138K `SKILL.md` files. Agent Skill portability/security tools were considered but rejected after discovery showed several active linters, scanners, lockfiles, and package managers already serving that space.

## Candidates considered

| Candidate | User pain | Differentiation | Decision |
|---|---|---|---|
| Agent Footprint | Terminal-driven changes are missing from editor change lists; Git omits ignored files | Zero-dependency before/after report across ignored files, mode bits, and symlinks | Selected |
| Agent Skill scanner/lockfile | Skills can expand an agent's trust surface | Weak: multiple mature scanners and lockfile tools already exist | Rejected as crowded |
| Visual RAG storage estimator | Late-interaction indexes can be large | Narrow calculator with model-specific assumptions | Rejected as low utility |
| Agent checkpoint wrapper | Interrupted work needs recovery | Native editor checkpoints and existing cross-agent tools cover it | Rejected by reuse-first principle |

## Scope decision

The first release detects final filesystem state under one root. It deliberately does not become a sandbox, watcher, rollback system, process tracer, or cloud audit service. Those require different trust guarantees and would weaken the one-day, inspectable project.
