# CI/CD 计划（GitHub Actions + Docker Compose）

本文档是本项目后续落地 CI/CD 的实施计划（不是最终实现），重点覆盖：

- GitHub Actions 做 CI/CD
- `docker compose` 管理前端 + 后端
- Unit Test + E2E Test
- 部署目标为腾讯云大陆服务器：需要考虑 GitHub 连接稳定性、依赖/镜像加速（例如 Astral `uv`）
- 使用腾讯云 TCR
---

## 1. 目标与原则

### 目标
- PR 阶段：自动跑前后端单测 + 基础质量检查，阻断明显回归。
- 主分支/发布：自动构建镜像并推送仓库；自动部署到腾讯云服务器；支持回滚。
- 全程可复现：依赖锁定（`uv.lock`、`bun.lock`）、镜像 tag 可追溯（commit SHA / tag）。

### 原则
- CI 与 CD 解耦：CI 使用 GitHub-hosted runner；CD 优先使用腾讯云上的 self-hosted runner（更贴近生产网络环境）。
- 生产只拉镜像不编译：生产机器上尽量只做 `docker compose pull && docker compose up -d`。
- 关键依赖都可镜像加速：Python/Node/Docker 镜像、系统包源（若需要）。

---

## 2. 目录与文件规划（建议）

在仓库根目录新增/整理：

- `docker-compose.yml`：本地开发（可包含热更新、dev volume）
- `docker-compose.prod.yml`：生产部署（只引用镜像，不做 build）
- `backend/Dockerfile`（或沿用根 `Dockerfile` 并补齐）+ `frontend/Dockerfile`：分别构建镜像
- `e2e/`：E2E 测试工程（建议 Playwright）
- `.github/workflows/ci.yml`：PR/Push 的测试与质量检查
- `.github/workflows/cd.yml`：main/tag 的构建发布与部署

---

## 3. Docker Compose 方案（建议）

### 服务拆分
- `backend`：Python 服务（当前在 `src/`）
- `frontend`：Vite/Bun（当前在 `frontend/`）
- （可选）`nginx`：统一反代与静态资源（生产环境更推荐）
- （可选）`e2e`：仅在 CI 启动，用于跑端到端测试
- （按需）`redis`/`postgres` 等依赖服务（若未来引入）

### 端口与网络
- `frontend`：对外 `80/443`（生产建议由 `nginx` 暴露）
- `backend`：仅内网端口（由 `nginx` 或 `frontend` 访问），避免直接公网暴露管理端口
- 使用 compose 默认 network；通过服务名互相访问（例如 `http://backend:8000`）

### 生产部署策略
- `docker-compose.prod.yml` 中：
  - `image: <registry>/<repo>/backend:<tag>`
  - `image: <registry>/<repo>/frontend:<tag>`
  - 通过 `.env` 或 `--env-file` 注入 `TAG`、API Key 等
- 服务器上以 release tag / commit SHA 为粒度部署与回滚：
  - 部署：拉取新 tag 并重启
  - 回滚：回到上一个 tag 并重启

---

## 4. 测试策略（Unit + E2E）

### 4.1 后端 Unit Test
- 测试框架：`pytest`（建议）
- 结构建议：`tests/`（与 `src/` 同级）
- 覆盖重点：
  - 核心业务逻辑（纯函数/工具/服务层）
  - 关键配置加载（`.env`/环境变量缺失时的错误提示）
- 在 `pyproject.toml` 增加 dev 依赖（示例：`pytest`、`pytest-asyncio`、`httpx` 等）

### 4.2 前端 Unit Test
- 当前已存在：`frontend/package.json` 中 `vitest`（`bun test` / `bun run test`）
- 覆盖重点：
  - 关键组件渲染、交互
  - API client 的输入/输出与错误处理（可使用 mock）

### 4.3 E2E Test（建议 Playwright）
- 目标：模拟用户链路，覆盖“前端页面 -> 调用后端 -> 返回结果”最短闭环
- 推荐方式（CI 中）：
  1) `docker compose up -d` 启动 `backend` + `frontend`（以及依赖服务）
  2) 健康检查就绪后运行 Playwright（可单独 job）
  3) 失败时上传 Playwright report/artifacts
- 关键点：
  - 测试环境使用专用 `.env.e2e`（避免用生产 key）
  - 后端暴露 health endpoint（用于 CI 等待就绪）

---

## 5. GitHub Actions 工作流设计

### 5.1 CI（`.github/workflows/ci.yml`）

触发：
- `pull_request`（必跑）
- `push` 到非主分支（可选）

Jobs 建议拆分（可并行）：
- `backend_unit`：
  - 安装 Python 3.12
  - 安装 `uv`
  - `uv sync --frozen`（依赖锁定）
  - 运行 `ruff`（可选）
  - `pytest`
- `frontend_unit`：
  - 安装 Bun
  - `bun install --frozen-lockfile`
  - `bun run lint`（可选）
  - `bun test`
- `e2e`：
  - `docker compose` 拉起服务
  - Playwright 跑测试
  - 上传 report（失败时也上传）

缓存建议：
- `uv` cache（通常为 `~/.cache/uv`）
- Bun cache / node_modules（视实际情况决定；优先缓存 lock 对应的下载缓存）

### 5.2 CD（`.github/workflows/cd.yml`）

触发：
- `push` 到 `main`
- `tag`（例如 `v*`）

步骤建议：
1) 读取版本标签（优先 tag；否则用短 SHA）
2) 构建并推送镜像（backend/frontend）
3) 部署到腾讯云（推荐 self-hosted runner 或 SSH）

部署方式（推荐顺序）：
- 推荐 A：腾讯云服务器上部署 self-hosted runner
  - 优点：依赖/镜像拉取走国内网络；部署执行更稳定；无需开放 SSH 给 GitHub IP
  - 缺点：需要维护 runner 生命周期与权限隔离
- 备选 B：GitHub Actions 通过 SSH 执行远程命令
  - 在服务器执行：`docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`

---

## 6. 镜像仓库与命名（建议）

使用腾讯云 TCR，以减少生产机器跨境拉取成本。

镜像命名建议：
- `backend:<tag>`
- `frontend:<tag>`

tag 规则建议：
- 发布：`vX.Y.Z`
- 日常：`sha-<shortsha>`（例如 `sha-a1b2c3d`）

---

## 7. 大陆地区加速与连接稳定性

### 7.1 GitHub 连接策略
- CD 尽量在腾讯云内执行（self-hosted runner），减少“GitHub -> 国内服务器”的长链路不确定性。
- 若必须 SSH 部署：
  - 为生产环境设置 GitHub Environment + 审批（避免误触发）
  - SSH key 仅赋予最小权限，并限制来源/命令（可选）

### 7.2 Python（Astral `uv`）镜像加速

在腾讯云服务器（或 self-hosted runner）配置 `uv` 的 index 镜像。

位置（Linux/Unix）：
- `~/.config/uv/uv.toml` 或 `/etc/uv/uv.toml`

示例（将 `url` 替换为你确认可用的 PyPI simple 镜像地址）：
```toml
[[index]]
url = "https://mirrors.tencent.com/pypi/simple"
default = true
```

CI 中也可以用同样方式在 job 里写入该文件，保证行为一致。

### 7.3 前端依赖（Bun/npm registry）加速
- 建议在腾讯云机器上配置 npm registry 镜像（通过 `.npmrc` 或环境变量），例如：
  - `registry=https://registry.npmmirror.com`
- 在 CI（GitHub-hosted runner）通常不需要，但在 self-hosted runner/生产构建时会显著提速。

### 7.4 Docker 镜像加速
- 生产服务器建议配置 Docker daemon 的 registry mirror（使用腾讯云提供的镜像加速地址），以提升拉取基础镜像与依赖镜像速度。
- 生产环境优先“拉取已构建镜像”，避免在国内机器上构建过程中大量跨境拉取。

---

## 8. Secrets 与环境变量管理

GitHub Secrets（建议）：
- `REGISTRY_USERNAME` / `REGISTRY_PASSWORD`（或 TCR 的临时 token/密钥方案）
- `SSH_HOST` / `SSH_USER` / `SSH_KEY`（仅当使用 SSH 部署）
- 业务密钥（例如 `GLM_API_KEY`、`LINEAR_API_KEY`）：只在运行环境注入，不写进镜像层

部署侧 `.env` 管理：
- 生产服务器保存 `.env.prod`（不进仓库）
- `docker compose --env-file .env.prod ...`

---

## 9. 实施里程碑（可按迭代调整）

### M1：CI 打通（优先）
- 补齐后端测试框架与最小用例（pytest）
- 前端 vitest 在 CI 可稳定运行
- CI 流水线在 PR 上强制执行（required checks）

### M2：E2E 落地
- 引入 Playwright 测试工程
- 增加 health check + compose 就绪等待
- 失败上传 report

### M3：CD 落地（推荐 self-hosted runner）
- 镜像构建与推送（后端/前端）
- 腾讯云部署（pull + up）
- 回滚策略与保留最近 N 个版本

---

## 10. 待你确认的问题（落地前需定稿）

1) 生产环境是否使用 `nginx` 统一入口（推荐）？
2) 镜像仓库选型：腾讯云 TCR / Docker Hub / GHCR？
3) 后端对外运行方式：是否使用 `uvicorn`/`gunicorn`，以及监听端口？
4) 是否采用 self-hosted runner（推荐）还是 SSH 部署？
