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
  - 打 tag（`v*`）：push 版本 tag（例如 `v0.1.0`）+ `sha-<shortsha>` + `latest`
  - 支持手动触发（`workflow_dispatch`）：可传入 `tag` 输入用于测试推送 tag（注意：推送的 tag 名称不一定与实际 Git tag 对应的 commit 一致，按需使用）

说明：
- 该 CD 工作流默认跑在 **GitHub-hosted runner（ubuntu-latest）** 上，便于零运维落地。
- 不需要自建 runner；GitHub 会提供运行环境与 Docker/Buildx。

需要在 GitHub 仓库设置以下 Secrets：
- `TCR_REGISTRY`：例如 `useccr.ccs.tencentyun.com`（建议用 `docs/tcr-speed-test.md` 的结果选一个最优入口）
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
- 准备 `.env`（既用于 compose 变量替换，也会注入到 `backend` 容器；不要提交到仓库）
- 准备一个部署目录（例如 `/opt/fastapi-cicd`）包含：
  - `docker-compose.prod.yml`
  - `.env`
  - 证书目录（默认读取宿主机 `/etc/nginx/certs`，通过 `CERTS_DIR` 可自定义）

### 2.1 `.env` 至少需要哪些变量

`docker-compose.prod.yml` 里有几个变量是“必填”的（缺了会直接报错或容器启动失败）：

- `TCR_REGISTRY`：你的 TCR registry 域名（例如 `useccr.ccs.tencentyun.com`）
- `TCR_NAMESPACE`：你的 TCR 命名空间
- `TAG`：镜像 tag（例如 `latest` / `v0.1.0`）
- `SERVER_NAME`：对外域名（Nginx 用于 `server_name`）

如果你启用 HTTPS（当前 prod 模板默认启用），还需要准备证书文件（见下一节）：

- `CERTS_DIR`（可选）：宿主机证书目录（默认 `/etc/nginx/certs`）

此外，你的后端业务环境变量（如 `GLM_API_KEY` 等）也建议放在同一个 `.env`，会通过 `env_file` 注入到 `backend` 容器。

一个最小可用示例（按需加上业务变量）：

```bash
TCR_REGISTRY=useccr.ccs.tencentyun.com
TCR_NAMESPACE=YOUR_NAMESPACE
TAG=latest

SERVER_NAME=api.example.com
CERTS_DIR=/etc/nginx/certs

# Backend env (examples)
GLM_API_KEY=...
LINEAR_API_KEY=...
```

### 2.2 Nginx 证书文件（必需）

`docker-compose.prod.yml` 默认会把宿主机 `${CERTS_DIR:-/etc/nginx/certs}` 挂载到容器 `/etc/nginx/certs`，并期望存在：

- `/etc/nginx/certs/origin.crt`
- `/etc/nginx/certs/origin.key`

如果你用 Cloudflare Origin Cert，可直接命名为上面两个文件；若你用其他证书，同样确保路径与文件名匹配即可。

首次登录 TCR（服务器上执行一次即可）：
```bash
docker login ${TCR_REGISTRY} -u ${TCR_USERNAME}
```

部署/更新到 `latest`（服务器上）：
```bash
export TCR_REGISTRY=useccr.ccs.tencentyun.com
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

---

## 3) 生产治理：为什么要用 Environments + 版本化标签

这一节面向第一次接触 CI/CD 的同学，解释**为什么这么做**以及**怎么做**。目标是：

- **生产部署可控**：必须审批、必须来自指定 tag，防止误操作
- **可追溯/可回滚**：生产永远指向一个明确版本（而不是漂移的 `latest`）
- **权限最小化**：生产 SSH/域名等敏感信息只暴露给生产部署作业

### 3.1 先把概念讲清楚：Git tag / 镜像 tag / GitHub Release 的关系

你会看到三种“tag”，它们不是一回事：

1) **Git tag**（例如 `v0.3.0`）
- 这是 Git 对某个 commit 的“命名指针”
- `git tag v0.3.0 <commit>` 之后推送到远端，GitHub Actions 可以用 `on.push.tags: ['v*']` 监听它

2) **镜像 tag**（例如 `fastapi-cicd-backend:v0.3.0`）
- 这是容器镜像的“引用名”，实际指向某个镜像 digest
- 我们在 CD 中让“镜像 tag 与 Git tag 同名”，这样一眼能对应到源码版本

3) **GitHub Release**
- 这是 GitHub 上的“发布条目”（Release notes + 附件）
- Release **一定绑定一个 Git tag**
- Release 不是 CI/CD 的必要条件；更像“公告/变更说明”的载体

推荐的落地方式：**用 Git tag 驱动构建与部署**，Release 作为可选的说明书。

### 3.2 镜像标签策略（Image Tagging Strategy）

生产环境推荐只部署“不可变标签（immutable tag）”，避免漂移：

- ✅ `vX.Y.Z`：发布版本标签（最直观、最适合回滚）
- ✅ `sha-<shortsha>`：提交标签（便于精确定位某次构建）
- ⚠️ `latest`：移动标签（会漂移），建议只用于开发/演示，不建议作为生产部署依赖

实践建议：

- 每次发布 `vX.Y.Z` 时，同时推送：
  - `...:vX.Y.Z`
  - `...:sha-<shortsha>`（同一 commit）
  - （可选）`...:latest`（指向最新发布）
- 生产部署时把 `.env` 里的 `TAG` 设置为 `vX.Y.Z`（或 `sha-*`），而不是 `latest`

### 3.3 用 GitHub Environments 管控生产（prod）

GitHub Environments 能解决两件事：

1) **生产部署要审批**（Required reviewers）
2) **生产 secrets 只能被生产部署 job 读取**（Environment secrets）

一次性配置步骤（在 GitHub 网页端）：

1. Repo → `Settings` → `Environments` → `New environment` → 创建 `prod`
2. 在 `prod` 里开启保护规则（建议）：
   - Required reviewers：至少 1 人（生产部署必须手动批准）
   - Deployment branches and tags：
     - 只允许 `tags` 匹配 `v*`（推荐：只有发布 tag 才能部署）
3. 把生产 secrets 放进 `prod`（Environment secrets），而不是仓库级 Secrets：
   - `PROD_SSH_HOST`：生产服务器 IP/域名
   - `PROD_SSH_USER`：SSH 用户名（建议 `deploy`，非 root）
   - `PROD_SSH_KEY`：SSH 私钥（只读、仅用于部署；建议 Ed25519）
   - `PROD_SSH_KNOWN_HOSTS`：服务器 host key（推荐用 `ssh-keyscan -H <host>` 生成）
   - `PROD_DEPLOY_PATH`：部署目录（默认 `/opt/fastapi-cicd`，可不填）

4. （可选）在 `prod` 里设置 Environment variables：
   - `PROD_HEALTHCHECK_URL`：例如 `https://api.example.com/health`（用于部署后健康检查；也可在手动触发时临时填写）

### 3.3.1 生成 SSH 密钥对

在你的本地电脑上生成一对 SSH 密钥（**不要把私钥提交到仓库**）：

```bash
ssh-keygen -t ed25519 -C "gh-deploy" -f ./gh_deploy_ed25519
```

这会生成两个文件：

| 文件 | 类型 | 用途 |
|------|------|------|
| `gh_deploy_ed25519` | 私钥 | 后续填入 GitHub Secret `PROD_SSH_KEY` |
| `gh_deploy_ed25519.pub` | 公钥 | 填入服务器 `/home/deploy/.ssh/authorized_keys` |

查看公钥内容（下一步会用到）：
```bash
cat gh_deploy_ed25519.pub
```

### 3.3.2 服务器侧准备（创建 deploy 用户 + 配置公钥）

生产机上建议创建一个专用用户 `deploy`，只允许 key 登录，并且只给它部署所需的最小权限：

1) 创建用户并配置公钥（将上一步生成的公钥内容填入）：

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo tee /home/deploy/.ssh/authorized_keys >/dev/null <<'EOF'
ssh-ed25519 AAAAC3Nza... 你的完整公钥内容
EOF
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
```

2) 让 `deploy` 能执行 docker（两种方式二选一）：
- 推荐：加入 `docker` 组（更简单）：

```bash
sudo usermod -aG docker deploy
```

- 或者：用 `sudo` 执行 docker（需要额外配置 sudoers；更细粒度但更麻烦）

3) 确保部署目录可访问：

```bash
sudo chown -R deploy:deploy /opt/fastapi-cicd
```

4) **以 deploy 用户身份登录 TCR**（必需）：

Docker 登录凭证按用户隔离存储，deploy 用户需要独立登录：

```bash
# 以 deploy 用户身份登录 TCR
sudo -u deploy docker login ${TCR_REGISTRY} -u ${TCR_USERNAME}
```

这会把凭证保存到 `/home/deploy/.docker/config.json`，之后 GitHub Actions 通过 SSH 以 deploy 用户执行部署时就能拉取镜像了。

（可选）加固 sshd（按你团队策略决定，改完记得验证不会把自己锁在门外）：
- 禁用密码登录：`PasswordAuthentication no`
- 禁止 root 直登：`PermitRootLogin no`

### 3.3.3 GitHub 侧准备（配置 Secrets）

1) **配置私钥**：将 `gh_deploy_ed25519`（私钥）内容填入 GitHub 仓库的 `prod` 环境 Secret `PROD_SSH_KEY`

2) **生成 known_hosts**（防止中间人攻击）：

在本地执行（替换 `<PROD_SSH_HOST>` 为你的服务器 IP 或域名）：

```bash
ssh-keyscan -H <PROD_SSH_HOST>
```

把输出整段复制进 GitHub Secret `PROD_SSH_KNOWN_HOSTS`（用于 StrictHostKeyChecking，避免中间人攻击）。

### 3.3.4 首次验证（推荐用手动触发）

第一次把 secrets/variables 配好后，建议先用手动触发验证链路是否通畅：

1) GitHub Actions → `deploy-prod` → Run workflow
- `tag`：填一个你已经推送到 TCR 的版本（例如 `v0.1.0`）
- `healthcheck_url`：你想检查的 URL（例如 `https://api.example.com/health`；不填则使用 `prod` 环境变量 `PROD_HEALTHCHECK_URL`）

2) 如果你开启了 Required reviewers，会看到 job 在 `prod` 环境处等待批准；批准后才会开始 SSH 部署。

### 3.4 发布与部署的推荐流水线（Tag-driven）

目标：你只要做一件事——打一个发布 tag（例如 `v0.3.0`），剩下都自动化且可追溯。

推荐流程：

1) **发布（打 Git tag）**：触发构建并推送镜像到 TCR
- `push v* tag` → 触发 `.github/workflows/tcr-cd.yml`
- 产物：两套镜像（backend/nginx）推到 TCR，并带上版本 tag

2) **部署到生产**：触发生产部署（需要审批）
- `v* tag` → 触发 `deploy-prod`
- 该 job 绑定 `environment: prod`，需要 reviewers 手动批准
- 部署方式：SSH 到服务器执行 `docker compose pull && docker compose up -d`
- 验收：跑健康检查（例如 `curl https://$SERVER_NAME/health`）

### 3.5 新手发布操作手册（推荐复制粘贴）

假设你要发布 `v0.3.0`，并且你希望这个版本对应当前 `main` 最新 commit：

```bash
git checkout main
git pull --ff-only

# 推荐用 annotated tag（便于写说明、也更符合发布语义）
git tag -a v0.3.0 -m "v0.3.0"
git push origin v0.3.0
```

然后在 GitHub 上确认：

- Actions 里 `tcr-cd` workflow 跑成功
- TCR 里能看到 `fastapi-cicd-backend:v0.3.0` 和 `fastapi-cicd-nginx:v0.3.0`

（可选）创建 GitHub Release：

- GitHub → Releases → Draft a new release → 选择 `v0.3.0` → 写变更说明 → Publish

生产回滚（原则上就是把服务器 `.env` 的 `TAG` 改回旧版本并重启）：

```bash
export TAG=v0.2.9
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```
