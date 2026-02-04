# 后端 CI/CD（GitHub Actions -> 腾讯云 TCR -> 服务器 docker compose）

当前阶段：仅后端 + nginx（先不管前端与测试）。

---

## 1) GitHub Actions

### CI：构建校验（不推送）
- 工作流：`.github/workflows/backend-ci.yml`
- 行为：构建 `backend` 与 `nginx` 镜像（不 push），用于尽早发现 Dockerfile/依赖问题。

### CD：推送到腾讯云 TCR
- 工作流：`.github/workflows/tcr-cd.yml`
- 触发：
  - 推送到 `main`：push 两个 tag（`sha-xxxxxxx` + `latest`）
  - 打 tag（`v*`）：push tag 本身（例如 `v0.1.0`）

需要在 GitHub 仓库设置以下 Secrets：
- `TCR_REGISTRY`：例如 `ccr.ccs.tencentyun.com`
- `TCR_NAMESPACE`：你的 TCR 命名空间
- `TCR_USERNAME`：TCR 登录用户名
- `TCR_PASSWORD`：TCR 登录密码/Token

镜像名固定为：
- `${TCR_REGISTRY}/${TCR_NAMESPACE}/fastapi-cicd-backend:<tag>`
- `${TCR_REGISTRY}/${TCR_NAMESPACE}/fastapi-cicd-nginx:<tag>`

---

## 2) 服务器部署（docker compose 拉取最新镜像）

生产 compose 文件：`docker-compose.prod.yml`

在服务器准备：
- 安装 Docker + Docker Compose v2
- 准备 `.env`（业务环境变量，不进仓库）
- 准备一个部署目录（例如 `/opt/fastapi-cicd`）包含：
  - `docker-compose.prod.yml`
  - `.env`
  - 证书目录（默认读取宿主机 `/etc/nginx/certs`，通过 `CERTS_DIR` 可自定义）

首次登录 TCR（服务器上执行一次即可）：
```bash
docker login ${TCR_REGISTRY} -u ${TCR_USERNAME}
```

部署/更新到 `latest`（服务器上）：
```bash
export TCR_REGISTRY=ccr.ccs.tencentyun.com
export TCR_NAMESPACE=YOUR_NAMESPACE
export TAG=latest

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

Nginx 容器可用的环境变量（用于配置域名、上游与流式路径）：
- `SERVER_NAME`：对外域名
- `UPSTREAM`：上游地址（默认 `http://backend:8080`）
- `STREAM_PATH_PREFIX`：流式接口路径前缀（默认 `/sync/`）
- `CERTS_DIR`：宿主机证书目录（默认 `/etc/nginx/certs`，容器内固定为 `/etc/nginx/certs`）

部署/回滚到指定版本（例如 `sha-a1b2c3d` 或 `v0.1.0`）：
```bash
export TAG=sha-a1b2c3d
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```
