这份文档用于量化 **GitHub-hosted runner → 腾讯云 TCR 多地域入口** 的链路质量，并把结果用 Python 可视化，辅助选择最优入口（主/备）用于后续镜像 push（以及评估 pull）。

本仓库已落地：

- 目标列表：`docs/tcr-speed-test.hosts.txt`
- 测速脚本（原始数据 + 汇总）：`scripts/tcr_speed_test.py`
- 可视化脚本：`scripts/tcr_speed_plot.py`
- 可手动触发的 GitHub Actions：`.github/workflows/tcr-speed-test.yml`
- Push/Pull 吞吐基准脚本：`scripts/tcr_push_pull_bench.py`
- Push/Pull 可视化脚本：`scripts/tcr_push_pull_plot.py`
- 可手动触发的 Push/Pull 基准：`.github/workflows/tcr-push-pull-bench.yml`

---

# GitHub Actions Runner → 腾讯云 TCR 多地域测速

## 1) 你会得到什么

一次跑完会产出 `tcr-speed-test-out/`：

- `raw.jsonl`：每个 host 每次 attempt 的明细（DNS/TCP/TLS/TTFB/Total）
- `summary.csv`：按 host 汇总的统计（median/mean/p90/min/max + success_rate）
- `summary.json`：同上，带参数与 targets
- `plot.png`：默认按 `end_to_end_ms_median` 的横向条形图

## 2) 测的是什么（以及为什么这样测）

我们用 `https://<host>/v2/` 做探测（Docker Registry v2 的常见入口）：

- `dns_ms`：DNS 解析耗时（Python `getaddrinfo`）
- `tcp_ms`：TCP 建连耗时（到 443）
- `tls_ms`：TLS 握手耗时
- `ttfb_ms`：HTTP 首字节时间（发送请求到收到第一个字节）
- `http_total_ms`：HTTP 从发请求到读完整个响应的耗时
- `end_to_end_ms`：整次 attempt 的总耗时（含上面所有步骤）

注意：这是“链路质量/时延”评估，不等同于“实际 push/pull 吞吐”。吞吐要用真实 push/pull 测（见第 5 节）。

## 3) 本地运行（可选）

仅需要 `python3`（脚本不依赖第三方包）：

```bash
python3 scripts/tcr_speed_test.py --hosts-file docs/tcr-speed-test.hosts.txt --repeats 5 --timeout 5
python3 -m pip install matplotlib
python3 scripts/tcr_speed_plot.py --summary-csv tcr-speed-test-out/summary.csv --out tcr-speed-test-out/plot.png
```

如果你想看其它指标（例如只关心 TLS）：

```bash
python3 scripts/tcr_speed_plot.py --metric tls_ms_median
```

### 用 `act` 在本地跑 GitHub Actions（可选）

如果你希望先在本地验证 workflow 是否可跑，可以用 `act` 执行 `workflow_dispatch`（产物目录会直接落在仓库根目录）。

1) 安装 `act`（按你本机系统安装即可）

2) 跑链路测速（不需要 secrets）：

```bash
act workflow_dispatch -W .github/workflows/tcr-speed-test.yml \
  --input repeats=3 \
  --input timeout=5 \
  --input insecure_tls=false \
  --input hosts_file=docs/tcr-speed-test.hosts.txt \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

3) 跑 push/pull 基准（需要 secrets + 允许容器里跑 docker）：

准备 `.secrets`（不要提交）：

```bash
cat > .secrets <<'EOF'
TCR_USERNAME=xxx
TCR_PASSWORD=xxx
TCR_NAMESPACE=xxx
TCR_BENCH_REPO=bench
EOF
```

然后执行（Linux 上通常需要挂载 docker socket；不同版本 act 可能参数略有差异）：

```bash
act workflow_dispatch -W .github/workflows/tcr-push-pull-bench.yml \
  --secret-file .secrets \
  --input repeats=2 \
  --input payload_mb=8 \
  --input hosts_file=docs/tcr-speed-test.hosts.txt \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

## 4) GitHub Actions 跑（推荐：真实 GitHub-hosted runner）

工作流：`.github/workflows/tcr-speed-test.yml`

触发方式：GitHub Actions → `tcr-speed-test` → Run workflow

输入参数（默认即可）：

- `repeats=5`
- `timeout=5`
- `hosts_file=docs/tcr-speed-test.hosts.txt`

跑完后在 artifacts 下载 `tcr-speed-test-out`，直接看 `summary.csv` 和 `plot.png`。

## 5) 用 push/pull 做“吞吐”拍板（推荐）

如果你最终要拍板“CI push 到哪个入口最省时”，建议跑一遍真实 push/pull 基准（和业务镜像尽量接近）。本仓库已提供：

- Workflow：`.github/workflows/tcr-push-pull-bench.yml`
- 输出目录：`tcr-push-pull-out/`（含 `summary.csv`、`push_plot.png`、`pull_plot.png`）

触发：GitHub Actions → `tcr-push-pull-bench` → Run workflow

需要 secrets（仓库 Settings → Secrets and variables → Actions）：

- `TCR_USERNAME`
- `TCR_PASSWORD`
- `TCR_NAMESPACE`
- `TCR_BENCH_REPO`（推荐专门建一个；脚本会 fallback 到 `TCR_REPO`）

基准做的事情：

- `docker login <host>`
- 构建一个小镜像（在镜像里塞入 `payload_mb` 大小的随机文件；用于避免 layer 去重导致“虚快”）
- `docker push` / `docker pull` 端到端计时（默认每个 host 跑 3 次）

注意事项：

- 多次 push 可能触发 layer 去重/复用，结果会偏乐观；想更“独立”，每轮改 Dockerfile 内容会放大网络量。
- 真实吞吐测试会产生临时 tag，个人版清理不太方便时建议跑完手动清理。

## 6) 结果解读（决策口径）

建议按这个顺序筛选：

1. 先看 `success_rate`：明显不稳定或失败的直接淘汰
2. 再看 `end_to_end_ms_median` 与 `end_to_end_ms_p90`：时延低 + 波动小优先
3. 如果要最终拍板“push 快”，用第 5 节做真实 push/pull 验证
