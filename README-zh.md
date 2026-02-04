# FastAPI CI/CD 项目

一个基于 AgentScope 的 AI 助手后端与现代 React 前端的全栈应用。

## 项目概述

**后端**：Python 3.12 + FastAPI + AgentScope Runtime
- 基于 ReActAgent 的 AI 助手（"Jarvis"）
- 支持多种大语言模型（GLM、SiliconFlow、ModelScope）
- 集成 Linear MCP（Model Context Protocol）
- 会话管理与状态持久化

**前端**：Vite + React (TanStack Start)
- TypeScript + Tailwind CSS v4
- AI SDK 流式响应集成
- TanStack Router 现代路由

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12、FastAPI、AgentScope、AgentScope Runtime |
| 前端 | React 19、Vite、TanStack Start、Tailwind CSS、Bun |
| 包管理 | uv (Python)、Bun (Node) |
| 容器化 | Docker、Docker Compose、Nginx |
| 测试 | Vitest (前端)、pytest (后端 - 计划中) |
| CI/CD | GitHub Actions、腾讯云 TCR |

## 快速开始

### 前置要求
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python 包管理器)
- [Bun](https://bun.sh/) (JavaScript 运行时)
- Docker (可选，用于容器化部署)

### 本地开发

1. **克隆并配置环境**
   ```bash
   git clone <repository-url>
   cd fastapi-cicd
   cp .env.example .env
   # 编辑 .env 填入你的 API 密钥 (GLM_API_KEY、LINEAR_API_KEY 等)
   ```

2. **后端设置**
   ```bash
   # 安装依赖
   uv sync --frozen

   # 运行后端 (默认: http://0.0.0.0:8080)
   uv run python -m src.server
   ```

3. **前端设置**
   ```bash
   cd frontend
   bun install --frozen-lockfile
   bun run dev    # http://localhost:3000
   ```

### Docker 开发

```bash
# 构建并启动所有服务（nginx + backend）
docker compose up --build

# 开发模式（Compose develop.watch 文件监听）
docker compose up --build --watch
```

### 生产部署（腾讯云 TCR）

后端 + nginx 镜像由 GitHub Actions（self-hosted runner）构建并推送到腾讯云 TCR。
服务器端使用 `docker-compose.prod.yml` 拉取镜像并启动服务。

需要的 GitHub Secrets 与服务器部署命令见：`docs/tcr-cicd.md`。

## 配置说明

### 环境变量

复制 `.env.example` 到 `.env` 并配置：

| 变量 | 说明 |
|------|------|
| `GLM_API_KEY` | GLM (智谱AI) API 密钥 |
| `SILICONFLOW_API_KEY` | SiliconFlow API 密钥 |
| `MODELSCOPE_API_KEY` | ModelScope API 密钥 |
| `LINEAR_API_KEY` | Linear MCP 集成 API 密钥 |
| `HOST` | 后端监听地址 (默认: `0.0.0.0`) |
| `PORT` | 后端端口 (默认: `8080`) |

### Nginx（Docker）环境变量

Nginx 配置通过模板 + 环境变量渲染：
- `NGINX_TEMPLATE`：`dev` 或 `prod`
- `SERVER_NAME`：域名（生产）或主机名（开发）
- `UPSTREAM`：上游地址（默认 `http://backend:8080`）
- `STREAM_PATH_PREFIX`：流式接口路径前缀（默认 `/sync/`）
- `CERTS_DIR`：宿主机证书目录（生产，默认 `/etc/nginx/certs`）

## 项目结构

```
fastapi-cicd/
├── .github/workflows/        # GitHub Actions（TCR CI/CD）
├── src/                      # Python 后端源码
│   ├── __init__.py
│   ├── server.py            # 后端入口
│   ├── agent_app.py         # AgentScope Agent 配置
│   └── daemon_deploy.py     # 部署守护进程
├── frontend/                 # React 前端
│   ├── src/
│   │   └── routes/
│   │       └── api/
│   │           └── chat.ts  # 聊天 API 集成
│   ├── package.json
│   └── bunfig.toml
├── nginx/                    # Nginx 镜像（配置由 env 渲染）
│   ├── Dockerfile
│   ├── docker-entrypoint.d/
│   └── templates/
├── docs/                     # 文档
│   ├── ci-cd-plan.md        # CI/CD 实施计划
│   └── tcr-cicd.md          # 后端 CI/CD 推送到腾讯云 TCR
├── tests/                    # 后端测试 (计划中)
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── docker-compose.yml
├── docker-compose.prod.yml   # 服务器部署（从 TCR 拉取）
├── Dockerfile
├── pyproject.toml           # Python 依赖
└── uv.lock                  # Python 依赖锁定
```

## 可用命令

### 后端

```bash
# 安装依赖
uv sync --frozen

# 运行开发服务器
uv run python -m src.server

# 代码检查 (添加 ruff 作为开发依赖后)
uv run ruff check src --fix
```

### 前端

```bash
cd frontend

# 安装依赖
bun install --frozen-lockfile

# 开发服务器
bun run dev

# 生产构建
bun run build

# 预览生产构建
bun run preview

# 运行测试
bun test

# 代码检查与格式化
bun run lint
bun run format
```

## CI/CD 计划

本项目包含：

- **已实现（仅后端）**：GitHub Actions 构建并推送 `backend` + `nginx` 镜像到腾讯云 TCR（见 `docs/tcr-cicd.md`）。
- **规划中**：后端/前端的单测 + E2E（见 `docs/ci-cd-plan.md`）。

更完整路线图见：`docs/ci-cd-plan.md`。

## 开发规范

### 代码风格
- **Python**：4 空格缩进，函数/变量使用 `snake_case`，类使用 `PascalCase`
- **前端**：变量使用 `camelCase`，React 组件使用 `PascalCase`
- **代码检查**：ruff (Python)、ESLint + Prettier (TypeScript/React)

### 提交规范
使用约定式提交：
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档变更
- `refactor:` - 代码重构
- `test:` - 测试相关

## 许可证

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
