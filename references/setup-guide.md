# 功能选配引导

当用户说「配置 ebook-downloader」「设置 ebook-downloader」「初始化 ebook 管道」或「setup ebook downloader」时，Agent 应按以下流程逐项引导用户完成功能选配。

核心原则：每一步先问用户「有没有」，有就对接，没有就给安装命令或降级方案。全部完成后输出一份环境变量模板供用户保存。

---

## 引导流程

Agent 按顺序逐项询问，不要一次性抛出所有问题。每项给一个默认推荐，用户可以直接说「用推荐的」或「跳过」。

### 第 1 项：图书元数据来源（步骤①，核心）

**作用：** 根据书名/ISBN/SS码检索图书的作者、出版社、内容提要等信息。

**询问：** 「你有本地图书数据库吗？」

**如果用户说「有」：** 询问数据库的 HTTP API 地址（默认 `http://localhost:10223`），记录为 `EBOOKDB_URL`。

**如果用户说「没有」：** 推荐安装 EbookDatabase，并给出 Docker 一键命令：

```
docker pull hellohistory/ebookdatabase:latest
mkdir -p ~/ebookdb/instance
# 从 https://github.com/Hellohistory/EbookDatabase/releases 下载 .db 文件放入 ~/ebookdb/instance/
docker run -d --name ebookdb -v ~/ebookdb/instance:/app/instance -p 10223:10223 hellohistory/ebookdatabase:latest
```

同时说明：不装也可以，管道会降级为纯 Anna's Archive 搜索，但会丢失 NLC 元数据校验和书葵网书签——这意味着步骤④ 的书签注入只能走降级A（仅目录页）。

### 第 2 项：下载管理器（步骤②，核心）

**作用：** 接收 Anna's Archive 的 MD5 哈希，下载 PDF 文件。内置 FlareSolverr 反爬虫。

**询问：** 「你有下载管理器（如 stacks）吗？」

**如果用户说「有」：** 询问 API 地址（默认 `http://localhost:7788`）和 API Key，记录为 `DOWNLOAD_MANAGER_URL` 和 `DOWNLOAD_API_KEY`。

**如果用户说「没有」：** 推荐安装 stacks + FlareSolverr，给出 docker-compose 一键命令：

```
mkdir -p ~/stacks/config ~/stacks/download ~/stacks/logs
cat > ~/stacks/docker-compose.yaml << 'EOF'
services:
  stacks:
    image: zelest/stacks:latest
    ports: ["7788:7788"]
    volumes:
      - ./config:/opt/stacks/config
      - ./download:/opt/stacks/download
      - ./logs:/opt/stacks/logs
    environment:
      - USERNAME=admin
      - PASSWORD=stacks
      - SOLVERR_URL=http://flaresolverr:8191
  flaresolverr:
    image: ghcr.io/flaresolverr/flaresolverr:latest
    ports: ["8191:8191"]
EOF
cd ~/stacks && docker compose up -d
```

启动后访问 `http://localhost:7788`，用 admin / stacks 登录，在 Settings 中生成 Admin API Key。

同时说明：不装也可以，管道会尝试直接用 curl 从 Anna's Archive 下载页面提取直链，但成功率较低（Anna's Archive 有 Cloudflare 保护）。如果用户在中国大陆，还需配置代理环境变量 `http_proxy`。

### 第 3 项：代理（步骤②，中国大陆用户需要）

**询问：** 「你在国内吗？访问外网需要代理吗？」

**如果用户说「需要」：** 询问代理地址（默认 `http://127.0.0.1:7890`），记录为 `http_proxy` 和 `https_proxy`。

**如果用户说「不需要」或「在国外」：** 跳过。

### 第 4 项：OCR 引擎（步骤③，核心）

**作用：** 将扫描件 PDF 转为可搜索 PDF（含文字层）。

**询问：** 「需要 OCR 功能吗？」

**如果用户说「需要」：** 推荐 ocrmypdf + PaddleOCR，给出安装命令：

```
pip install ocrmypdf ocrmypdf-paddleocr paddlepaddle paddleocr PyMuPDF
```

同时提醒 OCR 的两个关键注意事项：`--jobs 1` 是强制的（多线程会乱码），大 PDF 建议分批 OCR（每批 50 页）。

**如果用户说「不需要」：** OCR 步骤将被跳过。如果 PDF 本身已有文字层，管道会自动检测并跳过 OCR。

### 第 5 项：书签注入（步骤④，可选）

**作用：** 从书葵网获取图书目录，自动推断层级，注入 PDF 书签。

**询问：** 「需要书签注入功能吗？」

**如果用户说「需要」：** 确认依赖已安装（`pip install pymupdf pikepdf`）。说明书签来源需要步骤① 有书葵网爬虫，如果没有，只能走降级A（仅添加一条「目录」书签）。本仓库自带 `scripts/inject_bookmarks.py` 和 `scripts/parse_bookmark_hierarchy.py`，可直接使用。

**如果用户说「不需要」：** 跳过。

### 第 6 项：上传与分享（步骤⑤，可选）

**作用：** 将 PDF 上传到文件存储，生成分享直链。

**询问：** 「需要上传和分享功能吗？」

**如果用户说「需要」：** 推荐自托管方案，按复杂度排列：

- 轻量级：用 Python 的 `http.server` 或 `python3 -m http.server 8080` 临时分享
- 中等：部署 Z-File 网盘（Docker），支持直链生成
- 完整：Nextcloud / MinIO（S3 兼容），支持权限管理

询问用户选择哪种，然后给出对应的 Docker 命令或配置说明。记录 `UPLOAD_SERVICE_URL` 和 `UPLOAD_TOKEN`。

**如果用户说「不需要」：** 跳过。管道完成后只输出本地文件路径。

### 第 7 项：通知通道（步骤⑥，可选）

**作用：** 管道完成后发送结构化报告。

**询问：** 「需要完成通知吗？通过什么渠道？」

支持渠道：Telegram Bot（需 Bot Token 和 Chat ID）、飞书 Webhook、企业微信 Webhook、邮件（SMTP）。

根据用户选择，给出对应的配置说明，记录必要的 Token/URL。

**如果用户说「不需要」：** 报告输出到终端。

---

## 选配完成

全部 7 项询问完毕后，Agent 输出一份汇总，包含：

1. 已选配的功能清单（打勾的 + 打叉的）
2. 需要安装的软件列表（尚未安装的）
3. 一份可直接保存的环境变量模板，格式如下：

```bash
# === ebook-downloader 环境变量 ===

# 图书数据库（步骤①）
export EBOOKDB_URL="http://localhost:10223"

# 下载管理器（步骤②）
export DOWNLOAD_MANAGER_URL="http://localhost:7788"
export DOWNLOAD_API_KEY="sk-你的-API-Key"

# 代理（如需要）
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"

# 上传服务（如需要）
export UPLOAD_SERVICE_URL="http://your-host:32771"
export UPLOAD_TOKEN="你的-Token"
```

最后提示用户：「把上面的环境变量加到 `~/.bashrc` 或 `~/.zshrc`，然后重新打开终端。配置完成后，对我说『下载 《书名》』即可开始使用。」
