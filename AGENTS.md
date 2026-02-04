# Repository Guidelines

## Project Structure & Module Organization

- `src/`: Python backend entrypoints and app code (see `src/agent_app.py` and `src/server.py`).
- `docs/`: design notes and CI/CD planning (e.g., `docs/ci-cd-plan.md`).
- `frontend/`: Vite + React (TanStack Start) app.
- Root config: `pyproject.toml` + `uv.lock` (Python deps), `Dockerfile`/`docker-compose.yml` (containerized backend), `.env.example` (env var template).

## Build, Test, and Development Commands

Backend (Python 3.12; dependency manager: `uv`):
- Install deps: `uv sync --frozen`
- Run locally (default `HOST=0.0.0.0`, `PORT=8080`): `uv run python -m src.server`
- Run in Docker (includes live reload/sync via Compose “develop” watch): `docker compose up --build`

Frontend (Bun + Vite; runs on port 3000):
- Install deps: `cd frontend && bun install --frozen-lockfile`
- Dev server: `cd frontend && bun run dev`
- Build/preview: `cd frontend && bun run build` / `cd frontend && bun run preview`
- Lint/format: `cd frontend && bun run lint` / `cd frontend && bun run format`

## Coding Style & Naming Conventions

- Python: 4-space indentation, `snake_case` for functions/vars, `PascalCase` for classes. Keep modules importable (put runnable code behind `if __name__ == "__main__":`).
- Python linting: `ruff` is configured in `pyproject.toml` for import sorting (`I`). If you add it as a dev dependency, prefer `uv run ruff check src --fix`.
- Frontend: Prettier formats; ESLint enforces code quality. Use `camelCase` for variables and `PascalCase` for React components.

## Testing Guidelines

- Frontend: Vitest. Run `cd frontend && bun test`. Add tests next to code or under `frontend/src/**/__tests__/`.
- Backend: no `tests/` directory yet. When adding, use `pytest`, name files `test_*.py`, and run `uv run pytest`.

## Commit & Pull Request Guidelines

- Git history is currently a single `init` commit; no established convention yet. Use Conventional Commits (e.g., `feat: ...`, `fix: ...`) to keep history readable.
- PRs should include: a short description, how to test (commands + expected result), and screenshots for UI changes. Link related issues/tickets when applicable.

## Security & Configuration Tips

- Copy `.env.example` to `.env` for local development. Never commit real API keys (e.g., `GLM_API_KEY`, `LINEAR_API_KEY`).
