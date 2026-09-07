# Agent instructions — photosync

photosync — self-hosted photo library manager, 20 views.

- **Stack:** Python, FastAPI, SQLAlchemy, Vue 3, Tailwind, Pillow
- **Vault note:** `ProjectVault/01_Repositories/photosync.md` — read it for current status, history, and open loops before non-trivial work. It is canonical over anything stale here.
- **Runtime preflight:** python + pip; pytest (74 backend tests)
- **Deploy:** homelab; CI-published GHCR images via .github/workflows/docker-publish.yml -> docker-compose.homelab.yml

## Operating contract (Claude Code + Codex)

Austin's global rules live in `~/.claude/CLAUDE.md` + `CLAUDE-shared.md` (Claude Code) and
`~/.codex/AGENTS.md` (Codex) — same contract, both agents. Load-bearing: simplest viable
solution first (no new scripts/infra unless asked), confirm the path before editing, todos are
per-project (never a global TASKS.md), commit/push only when asked and branch off the default
first, session-end `/document` capture to the vault if the work produced a decision/fix/learning.
