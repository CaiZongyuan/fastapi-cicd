# FastAPI CI/CD Project

A full-stack application with an AI assistant backend powered by AgentScope and a modern React frontend.

## Project Overview

**Backend**: Python 3.12 + FastAPI + AgentScope Runtime
- ReActAgent-based AI assistant ("Jarvis")
- Multi-LLM support (GLM, SiliconFlow, ModelScope)
- MCP (Model Context Protocol) integration with Linear
- Session management with state persistence

**Frontend**: Vite + React (TanStack Start)
- TypeScript with Tailwind CSS v4
- AI SDK integration for streaming responses
- Modern routing with TanStack Router

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, AgentScope, AgentScope Runtime |
| Frontend | React 19, Vite, TanStack Start, Tailwind CSS, Bun |
| Package Management | uv (Python), Bun (Node) |
| Containerization | Docker, Docker Compose, Nginx |
| Testing | Vitest (frontend), pytest (backend - planned) |
| CI/CD | GitHub Actions, Tencent Cloud TCR |

## Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Bun](https://bun.sh/) (JavaScript runtime)
- Docker (optional, for containerized deployment)

### Local Development

1. **Clone and setup environment**
   ```bash
   git clone <repository-url>
   cd fastapi-cicd
   cp .env.example .env
   # Edit .env with your API keys (GLM_API_KEY, LINEAR_API_KEY, etc.)
   ```

2. **Backend setup**
   ```bash
   # Install dependencies
   uv sync --frozen

   # Run backend (default: http://0.0.0.0:8080)
   uv run python -m src.server
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   bun install --frozen-lockfile
   bun run dev    # http://localhost:3000
   ```

### Docker Development

```bash
# Build and start all services (nginx + backend)
docker compose up --build

# Development mode with file watching (Compose develop.watch)
docker compose up --build --watch
```

### Production (Tencent Cloud TCR)

Backend-only + nginx images are built and pushed by GitHub Actions (GitHub-hosted runner) to Tencent Cloud TCR.
Server-side deploy uses `docker-compose.prod.yml` to pull images and start services.

See `docs/tcr-cicd.md` for required GitHub Secrets and server deploy commands.
See `docs/tcr-cicd.md` for production governance (GitHub Environments + tag-driven releases).

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description |
|----------|-------------|
| `GLM_API_KEY` | GLM (智谱AI) API key |
| `SILICONFLOW_API_KEY` | SiliconFlow API key |
| `MODELSCOPE_API_KEY` | ModelScope API key |
| `LINEAR_API_KEY` | Linear API key for MCP integration |
| `HOST` | Backend host (default: `0.0.0.0`) |
| `PORT` | Backend port (default: `8080`) |

### Nginx (Docker) Environment Variables

Nginx config is rendered from templates via env vars:
- `NGINX_TEMPLATE`: `dev` or `prod`
- `SERVER_NAME`: domain (prod) or host (dev)
- `UPSTREAM`: backend upstream (default: `http://backend:8080`)
- `STREAM_PATH_PREFIX`: streaming path prefix (default: `/sync/`)
- `CERTS_DIR`: host path to certs (prod, default: `/etc/nginx/certs`)

## Project Structure

```
fastapi-cicd/
├── .github/workflows/        # GitHub Actions (TCR CI/CD)
├── src/                      # Python backend source
│   ├── __init__.py
│   ├── server.py            # Backend entry point
│   ├── agent_app.py         # AgentScope agent configuration
│   └── daemon_deploy.py     # Deployment daemon
├── frontend/                 # React frontend
│   ├── src/
│   │   └── routes/
│   │       └── api/
│   │           └── chat.ts  # Chat API integration
│   ├── package.json
│   └── bunfig.toml
├── nginx/                    # Nginx image (env-templated config)
│   ├── Dockerfile
│   ├── docker-entrypoint.d/
│   └── templates/
├── docs/                     # Documentation
│   ├── ci-cd-plan.md        # CI/CD implementation plan
│   └── tcr-cicd.md          # Backend CI/CD to Tencent Cloud TCR
├── tests/                    # Backend tests (planned)
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── docker-compose.yml
├── docker-compose.prod.yml   # Server deployment (pull from TCR)
├── Dockerfile
├── pyproject.toml           # Python dependencies
└── uv.lock                  # Locked Python dependencies
```

## Available Commands

### Backend

```bash
# Install dependencies
uv sync --frozen

# Run development server
uv run python -m src.server

# Lint code (after adding ruff as dev dependency)
uv run ruff check src --fix
```

### Frontend

```bash
cd frontend

# Install dependencies
bun install --frozen-lockfile

# Development server
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview

# Run tests
bun test

# Lint and format
bun run lint
bun run format
```

## CI/CD Plan

This project includes:

- **Implemented (backend-only)**: GitHub Actions builds and pushes `backend` + `nginx` images to Tencent Cloud TCR (see `docs/tcr-cicd.md`).
- **Planned**: Full CI (unit + E2E) for backend/frontend (see `docs/ci-cd-plan.md`).

See `docs/ci-cd-plan.md` for the broader roadmap.

## Development Guidelines

### Code Style
- **Python**: 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes
- **Frontend**: `camelCase` for variables, `PascalCase` for React components
- **Linting**: ruff (Python), ESLint + Prettier (TypeScript/React)

### Commit Convention
Use Conventional Commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions/changes

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
