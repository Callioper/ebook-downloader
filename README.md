# Ebook Downloader — Agent Skill

一个 **7 步骤电子书下载自动化管道**的通用参考架构。从书名/ISBN/SS 码出发，输出带 OCR 文字层和多级书签的 PDF + 分享直链。

> ⚠️ **这不是开箱即用的工具。** 它是一个可被 AI Agent 加载的 **SKILL.md 指令文件**——Agent 读取它后就知道如何编排下载管道。但管道中的每个步骤都依赖你**自建的基础设施**。详见 [适配备忘](#适配备忘)。

---

## 快速开始

### 方式一：npx skills（通用，支持 50+ Agent）

```bash
# 安装到所有检测到的 Agent
npx skills add Callioper/ebook-downloader

# 全局安装（跨项目可用）
npx skills add Callioper/ebook-downloader -g

# 只安装给特定 Agent
npx skills add Callioper/ebook-downloader -a claude-code -a opencode -a hermes
```

### 方式二：Hermes Agent 专用

```bash
# 搜索并安装
hermes skills search ebook-download
echo y | hermes skills install skills-sh/Callioper/ebook-downloader

# 或直接从 GitHub 安装
hermes skills install github/Callioper/ebook-downloader
```

### 方式三：手动安装（任意 Agent）

```bash
# 克隆到 Agent 的 skills 目录
git clone https://github.com/Callioper/ebook-downloader.git \
  ~/.hermes/skills/productivity/ebook-downloader/

# OpenClaw
git clone https://github.com/Callioper/ebook-downloader.git \
  ~/.openclaw/skills/ebook-downloader/

# Claude Code
git clone https://github.com/Callioper/ebook-downloader.git \
  ~/.claude/skills/ebook-downloader/
```

### 所有 Agent 安装速查表

以下是 40+ 种 AI Agent 的安装路径。`npx skills` 会自动选择正确的路径，手动安装时对照此表 `git clone`。

| Agent | `--agent` 参数 | 项目路径 | 全局路径 | 安装命令（手动） |
|-------|---------------|---------|---------|----------------|
| **Claude Code** | `claude-code` | `.claude/skills/` | `~/.claude/skills/` | `git clone ... ~/.claude/skills/ebook-downloader/` |
| **Codex** | `codex` | `.agents/skills/` | `~/.codex/skills/` | `git clone ... ~/.codex/skills/ebook-downloader/` |
| **Cursor** | `cursor` | `.agents/skills/` | `~/.cursor/skills/` | `git clone ... ~/.cursor/skills/ebook-downloader/` |
| **Windsurf** | `windsurf` | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` | `git clone ... ~/.codeium/windsurf/skills/ebook-downloader/` |
| **Cline** | `cline` | `.agents/skills/` | `~/.agents/skills/` | `git clone ... ~/.agents/skills/ebook-downloader/` |
| **Roo Code** | `roo` | `.roo/skills/` | `~/.roo/skills/` | `git clone ... ~/.roo/skills/ebook-downloader/` |
| **GitHub Copilot** | `github-copilot` | `.agents/skills/` | `~/.copilot/skills/` | `git clone ... ~/.copilot/skills/ebook-downloader/` |
| **Gemini CLI** | `gemini-cli` | `.agents/skills/` | `~/.gemini/skills/` | `git clone ... ~/.gemini/skills/ebook-downloader/` |
| **Antigravity** | `antigravity` | `.agents/skills/` | `~/.gemini/antigravity/skills/` | `git clone ... ~/.gemini/antigravity/skills/ebook-downloader/` |
| **OpenCode** | `opencode` | `.agents/skills/` | `~/.config/opencode/skills/` | `git clone ... ~/.config/opencode/skills/ebook-downloader/` |
| **Amp** | `amp` | `.agents/skills/` | `~/.config/agents/skills/` | `git clone ... ~/.config/agents/skills/ebook-downloader/` |
| **Trae** | `trae` | `.trae/skills/` | `~/.trae/skills/` | `git clone ... ~/.trae/skills/ebook-downloader/` |
| **Trae CN** | `trae-cn` | `.trae/skills/` | `~/.trae-cn/skills/` | `git clone ... ~/.trae-cn/skills/ebook-downloader/` |
| **Kiro CLI** | `kiro-cli` | `.kiro/skills/` | `~/.kiro/skills/` | `git clone ... ~/.kiro/skills/ebook-downloader/` |
| **Augment** | `augment` | `.augment/skills/` | `~/.augment/skills/` | `git clone ... ~/.augment/skills/ebook-downloader/` |
| **CodeBuddy** | `codebuddy` | `.codebuddy/skills/` | `~/.codebuddy/skills/` | `git clone ... ~/.codebuddy/skills/ebook-downloader/` |
| **Qwen Code** | `qwen-code` | `.qwen/skills/` | `~/.qwen/skills/` | `git clone ... ~/.qwen/skills/ebook-downloader/` |
| **Goose** | `goose` | `.goose/skills/` | `~/.config/goose/skills/` | `git clone ... ~/.config/goose/skills/ebook-downloader/` |
| **Continue** | `continue` | `.continue/skills/` | `~/.continue/skills/` | `git clone ... ~/.continue/skills/ebook-downloader/` |
| **AiderDesk** | `aider-desk` | `.aider-desk/skills/` | `~/.aider-desk/skills/` | `git clone ... ~/.aider-desk/skills/ebook-downloader/` |
| **Droid** | `droid` | `.factory/skills/` | `~/.factory/skills/` | `git clone ... ~/.factory/skills/ebook-downloader/` |
| **Devin** | `devin` | `.devin/skills/` | `~/.config/devin/skills/` | `git clone ... ~/.config/devin/skills/ebook-downloader/` |
| **IBM Bob** | `bob` | `.bob/skills/` | `~/.bob/skills/` | `git clone ... ~/.bob/skills/ebook-downloader/` |
| **Kilo Code** | `kilo` | `.kilocode/skills/` | `~/.kilocode/skills/` | `git clone ... ~/.kilocode/skills/ebook-downloader/` |
| **Mistral Vibe** | `mistral-vibe` | `.vibe/skills/` | `~/.vibe/skills/` | `git clone ... ~/.vibe/skills/ebook-downloader/` |
| **Cortex Code** | `cortex` | `.cortex/skills/` | `~/.snowflake/cortex/skills/` | `git clone ... ~/.snowflake/cortex/skills/ebook-downloader/` |
| **MCPJam** | `mcpjam` | `.mcpjam/skills/` | `~/.mcpjam/skills/` | `git clone ... ~/.mcpjam/skills/ebook-downloader/` |
| **Junie** | `junie` | `.junie/skills/` | `~/.junie/skills/` | `git clone ... ~/.junie/skills/ebook-downloader/` |
| **Pi** | `pi` | `.pi/skills/` | `~/.pi/agent/skills/` | `git clone ... ~/.pi/agent/skills/ebook-downloader/` |
| **Kode** | `kode` | `.kode/skills/` | `~/.kode/skills/` | `git clone ... ~/.kode/skills/ebook-downloader/` |
| **Zencoder** | `zencoder` | `.zencoder/skills/` | `~/.zencoder/skills/` | `git clone ... ~/.zencoder/skills/ebook-downloader/` |
| **Neovate** | `neovate` | `.neovate/skills/` | `~/.neovate/skills/` | `git clone ... ~/.neovate/skills/ebook-downloader/` |
| **Pochi** | `pochi` | `.pochi/skills/` | `~/.pochi/skills/` | `git clone ... ~/.pochi/skills/ebook-downloader/` |
| **AdaL** | `adal` | `.adal/skills/` | `~/.adal/skills/` | `git clone ... ~/.adal/skills/ebook-downloader/` |
| **Hermes Agent** | `hermes` | — | `~/.hermes/skills/` | `hermes skills install github/Callioper/ebook-downloader` |
| **OpenClaw** | `openclaw` | `skills/` | `~/.openclaw/skills/` | `git clone ... ~/.openclaw/skills/ebook-downloader/` |

> **提示：** 不确定你的 Agent 名称？运行 `npx skills add Callioper/ebook-downloader` 不加 `-a` 参数，CLI 会自动检测已安装的 Agent 并让你选择。

### Agent 专属配置

某些 Agent 需要额外配置才能加载 skill：

**OpenClaw** — 需要在 `~/.openclaw/config.yaml` 中声明 skill 路径，或确保 `allowed-tools` 包含 skill 所需的工具（terminal、python 等）：

```yaml
# ~/.openclaw/config.yaml
skills:
  paths:
    - ~/.openclaw/skills/
```

**Kiro CLI** — 默认自动加载 `~/.kiro/skills/`，无需额外配置。如果使用自定义 Agent，在 `~/.kiro/agents/<agent>.json` 中添加：

```json
{
  "resources": ["skill://~/.kiro/skills/**/SKILL.md"]
}
```

**GitHub Copilot** — 在 VS Code 中安装后，Copilot Chat 会自动发现 `.agents/skills/` 或 `~/.copilot/skills/` 下的 SKILL.md。无需额外配置。

**Augment / Cursor / Windsurf** — 使用 `.agents/skills/`（项目级）或各自全局路径。这些 Agent 通常会自动扫描 skills 目录。

---

## 这个 Skill 做什么

当你的 AI Agent 加载此 skill 后，在你说「帮我下载《XXX》这本书」时，Agent 会按以下管道执行：

```
用户说「下载 《形而上学的巴别塔》」
    │
    ▼
┌─────────────────┐
│ ① 检索元数据     │  本地 DB 模糊搜索 → NLC 校验 → 书葵网取书签
│ 输出：书名/ISBN/ │
│ SS码/书签文本     │
└────────┬────────┘
         ▼
┌─────────────────┐
│ ② 下载 PDF       │  Anna's Archive 搜 MD5 → 下载管理器排队 → 轮询完成
│ 输出：本地 PDF    │  （文件类型自动修正：.zip→.pdf、PDG→PDF）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③ OCR            │  ocrmypdf + PaddleOCR（--jobs 1 防乱码）
│ 输出：可搜索 PDF  │  后验证 CJK 文字比率
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③.5 压缩         │  ocrmypdf --optimize 1 或 qpdf --recompress-flate
│ ⛔ 禁止 GS       │  （Ghostscript pdfwrite 摧毁 OCR 文字层）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ④ 生成书签       │  书葵网书签优先 → 降级A（仅目录页）→ 降级B（AI Vision）
│ 输出：带多级书签  │  栈深度模型自动推断"部分>章>节>一、"层级
│ PDF + 规范文件名  │  命名：书名_作者（YYYYMMDD）.pdf
└────────┬────────┘
         ▼
┌─────────────────┐
│ ⑤ 上传 + 直链    │  REST API 两步上传 → 30 天直链
│ 输出：分享 URL    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ ⑥ 生成报告       │  结构化汇报：元数据 / 文件大小 / OCR 结果 / 书签来源 / 链接
└─────────────────┘
```

---

## 前置依赖

### 你必须自建的基础设施

| 步骤 | 需要什么 | 推荐方案 |
|------|---------|---------|
| ① 检索 | 图书元数据来源 | 本地 SQLite/PostgreSQL + [NLC 联合编目 API](http://opac.nlc.cn) |
| ① 检索 | 书签数据源 | [书葵网 shukui.net](https://shukui.net) 爬虫 |
| ② 下载 | 下载管理器 | [stacks](https://github.com/annas-archive/stacks) Docker 或自建队列 |
| ② 下载 | 外网代理（中国大陆） | Clash/V2Ray（127.0.0.1:7890） |
| ③ OCR | ocrmypdf | `pip install ocrmypdf ocrmypdf-paddleocr` |
| ③ OCR | PaddleOCR | `pip install paddlepaddle paddleocr` |
| ⑤ 上传 | 文件存储 + 直链 | [Z-File](https://github.com/zhaojun1998/zfile) / Nextcloud / MinIO |
| ⑤ 上传 | 内网穿透（外网分享） | [cpolar](https://cpolar.com) / Cloudflare Tunnel / frp |
| ⑥ 报告 | 消息通道 | Telegram Bot API / 飞书 / 企业微信 |

### 环境变量（Agent 加载 skill 前配置）

```bash
# 下载管理器
export DOWNLOAD_MANAGER_URL="http://localhost:7788"
export DOWNLOAD_API_KEY="sk-xxxxxxxx"

# 上传服务
export UPLOAD_SERVICE_URL="http://your-zfile-host:32771"
export UPLOAD_TOKEN="your-auth-token"

# 代理（如需要）
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
```

### 安装后验证

装完 skill 后，用以下方法确认 Agent 已正确加载：

**npx skills 方式：** 运行 `npx skills list`，输出中应出现 `ebook-downloader`。如果没出现，检查是否加了 `-g`（全局安装）但查询时没加 `-g`。

**手动 git clone 方式：** 确认 SKILL.md 在正确的路径下。以 Claude Code 为例，运行 `ls ~/.claude/skills/ebook-downloader/SKILL.md` 应返回文件路径。

**功能验证：** 在你的 Agent 中说「帮我查一下 ebook-downloader skill 的步骤」，如果 Agent 能正确列出 7 个步骤，说明 skill 已加载。

**常见安装故障：**

- `npx skills: command not found` — Node.js 版本需要 ≥ 18。运行 `node --version` 检查。如果版本过低，用 `nvm install 20` 升级。
- `git clone` 权限拒绝 — 确认仓库是公开的（https://github.com/Callioper/ebook-downloader 可以在浏览器打开）。如果用了 SSH 地址但没配 SSH key，改用 HTTPS 地址。
- Agent 不识别 skill — 确认 SKILL.md 在 Agent 扫描的目录下。部分 Agent（如 OpenClaw）需要在配置文件中显式声明 skills 路径，见上方「Agent 专属配置」。
- `npx skills add` 克隆仓库超时 — GitHub 在某些地区访问慢。可以先 `git clone` 到本地，再用 `npx skills add ./local-path` 从本地路径安装。

---

## 架构决策记录

### 1. 为什么不直接用 EbookDatabase 的 MD5 下载？

```
EbookDatabase second_pass_code 格式：
  944b8c6fc6d9076...#6cea7d57cd9e0bf5...#11440378#12928975_何为女性.zip
  └─ MD5 part1 ─┘#└─ MD5 part2 ─┘#filesize#filename
  ↑ 这是 DuXiu 内部格式，下载管理器不接受

Anna's Archive 真实 MD5：
  21a20f838a2bc8a8efe5e4b1073dc1cf
  ↑ 这才是可用的下载标识符
```

**结论：** 绕过本地数据库的 MD5，直接从 Anna's Archive 搜索页提取真实 MD5。

### 2. 为什么 OCR 必须 --jobs 1？

PaddleOCR + ocrmypdf 在多线程模式下（`--jobs > 1`）会 **100% 静默产生乱码**——PDF 看起来正常，但文字层的中文全部损坏。根因是 PaddlePaddle 的线程冲突导致文本编码错误。

**防御方案：**
- 强制 `--jobs 1`
- OCR 后用 `is_ocr_readable()` 检测 CJK 字符比率

### 3. 为什么不能用 Ghostscript 压缩？

实测：Ghostscript `-sDEVICE=pdfwrite` 处理后，《社会形态学》207 页的 OCR 文字层 **CJK=0，全部丢失**。

**正确方案：**
- `ocrmypdf --optimize 1`（内置安全优化）
- `qpdf --recompress-flate`（纯结构压缩，不触文字层）

### 4. 书签为什么有三层降级？

| 优先级 | 来源 | 触发条件 |
|--------|------|---------|
| 第一 | 书葵网书签 | 步骤① 拿到了书签文本 |
| 降级A | 仅目录页 | 书葵网页面存在但书签为空 |
| 降级B | AI Vision | 用户明确说「用 AI 识别目录」 |

降级A 是默认行为——因为从 OCR 提取目录页文字来确定 offset 在实践中不可靠。

---

## 适配备忘：把你的环境接进来

对照下表，把「原版实现」换成你自己的方案：

| 步骤 | 原版实现 | 接口契约 | 你替换为 |
|------|---------|---------|---------|
| ① | EbookDatabase HTTP API (localhost:10223) | `GET /search?q={keyword}` → JSON | 你自己的元数据源 |
| ① | NLC 联合编目 API | `nlc_isbn(isbn)` → {title, author, publisher, comments, tags} | 其他书目 API |
| ① | 书葵网爬虫 (shukui.net) | `bookmarkget(isbn)` → 书签纯文本 | 其他书签来源 |
| ② | Anna's Archive 搜索 | `curl annas-archive.gd/search?q={query}` → HTML → `/md5/{hash}` | 同（公网服务） |
| ② | stacks Docker (localhost:7788) | `POST /api/queue/add {"md5":"..."}` → 下载到磁盘 | 任何 HTTP 下载管理器 |
| ③ | ocrmypdf + PaddleOCR | CLI 命令（见 SKILL.md 步骤 3） | 同或 Tesseract（CJK 效果差） |
| ④ | pikepdf/PyMuPDF 注入 | `inject_bookmarks(pdf, tree)` | 同（Python 库） |
| ⑤ | Z-File (内网:32771) | 两步上传：`POST presign` → `PUT file` | S3 Presigned URL / Nextcloud WebDAV |
| ⑤ | cpolar 隧道 | 内网 32771 → `https://zfile.vip.cpolar.top` | Cloudflare Tunnel / frp |
| ⑥ | Telegram Bot API | `sendMessage` | 飞书 / 企业微信 / 邮件 |

### 最小可行适配

如果你只想验证管道，可以先搭这些：

1. **步骤②** 是硬依赖——必须有 Anna's Archive 搜索（公网）和下载管理器
2. **步骤③** 可以用 `ocrmypdf --skip-text` 跳过（如果 PDF 已有文字层）
3. **步骤④** 可以用 pikepdf 写死一个「目录页」书签作为降级A
4. **步骤⑤⑥** 可以暂时用本地文件 + `ls -lh` 代替

---

## 在你的 Agent 中触发

Agent 加载此 skill 后，以下关键词会触发管道：

- 「下载 《书名》」
- 「帮我找 《书名》」
- 「检索并下载 ISBN 978-7-xxx-xxxxx-x」
- 「用 SS 码 12662374 下载」

Agent 会自动按 SKILL.md 中的 7 步骤编排，逐步确认或自动执行。

### 不同 Agent 的行为差异

| Agent | 工具调用方式 | 注意事项 |
|-------|------------|---------|
| **Hermes Agent** | `execute_code`（本地脚本）+ `terminal`（外网 curl） | 外网必须用 terminal（沙盒不走代理） |
| **OpenClaw** | `terminal` / `bash` | 需要配置 `allowed-tools` |
| **Claude Code** | Bash 工具 | 需确保代理环境变量已设 |
| **Codex** | Shell 工具 | 支持 background 任务（OCR 可后台跑） |
| **npx skills 安装的 Agent** | 取决于具体 Agent | skill 指令是通用的，工具映射由 Agent 自己处理 |

---

## OCR 错误速查

如果你在步骤③ 遇到问题：

| 错误 | 原因 | 修复 |
|------|------|------|
| `--jobs > 1` → 文字层全部乱码 | PaddlePaddle 线程冲突 | 强制 `--jobs 1` |
| WSL2 `/tmp` 清理 → `FileNotFoundError` | 长进程间 `/tmp` 被 systemd 清理 | `TMPDIR=/path/to/fixed/dir` |
| DPI=0 → `ZeroDivisionError` | 部分 PDF 元数据 DPI=0 | ocrmypdf 已内置补丁 |
| `KeyError: 'text_word_region'` | PaddleOCR 2.9.1+ API 变化 | Patch `ocrmypdf_paddleocr/engine.py` |

---

## 常见问题排查

如果管道在某一步中断，下面是按步骤组织的排查指南。

### 步骤①：检索元数据

**症状：** 输入书名后返回「未找到」。

先确认数据源可用。如果依赖本地数据库，测试连通性：`curl http://localhost:10223/search?q=测试`。如果返回空或超时，检查数据库服务是否在运行。

如果数据库正常但搜不到结果，尝试换检索词。书名中的标点符号（如「·」「——」）可能导致模糊搜索失败，去掉标点重试。

如果依赖 NLC 联合编目，注意 NLC 主要收录学术专著和政府出版物——通俗小说、网络文学、外文原版书通常查不到，这不是 bug。

### 步骤②：下载 PDF

**症状：** Anna's Archive 搜索返回空或超时。

Anna's Archive 域名在部分地区被封锁。确认代理环境变量（`http_proxy`、`https_proxy`）已设置且代理端口正确。可以先用 `curl -x http://127.0.0.1:7890 https://annas-archive.gd` 测试代理是否通。

如果代理正常但仍超时，可能是 Anna's Archive 本身宕机。它偶尔会维护，等待 1-2 小时后重试。

**症状：** 下载管理器不响应（连接拒绝）。

下载管理器通常以 Docker 容器运行。运行 `docker ps | grep stacks` 确认容器在跑。如果没在跑，`docker start stacks` 启动它。

如果根本没装下载管理器，参考 [stacks 部署指南](https://github.com/annas-archive/stacks)。部署后需要先导入一些 MD5 才能测试下载功能。

**症状：** 下载完成但文件是 `.zip` 且无法直接打开。

正常现象。管道会自动检测文件类型：
- zip 内是单文件 PDF → 自动提取并重命名为 `.pdf`
- zip 内是 PDG/JPG 图片组 → 自动合成为 PDF
如果自动检测失败，手动用 `file downloaded.zip` 查看真实类型，用 `unzip -l downloaded.zip` 查看内容。

### 步骤③：OCR

**症状：** OCR 后中文文字层全是乱码/空白。

这是最常见的 OCR 问题。99% 的情况是因为 `--jobs` 参数 > 1。PaddleOCR 在多线程下存在编码损坏的 bug，强制使用 `--jobs 1`。

如果已经用了 `--jobs 1` 但仍然乱码，检查 PaddleOCR 版本。3.0+ 的 `predict()` 返回值格式有变化，需要确认 ocrmypdf-paddleocr 插件是否兼容。可以降级到 PaddleOCR 2.8.x 试试。

**症状：** OCR 进程被 kill（OOM）。

大 PDF（>500 页）OCR 时内存消耗大。解决方案：用 `--pages 1-50`、`--pages 51-100` 等分批 OCR，最后用 pikepdf 合并。每批 50 页是一个安全的值。

### 步骤④：书签注入

**症状：** pikepdf 报 `PdfError` 或权限错误。

PDF 可能设置了所有者密码（即使打开不需要密码）。用 `qpdf --decrypt input.pdf output.pdf` 移除限制后重试。注意这不能破解用户密码，只能移除编辑/打印限制。

**症状：** 注入的书签页码对不上。

PDF 的「逻辑页码」和「物理页码」可能不一致。比如封面、目录、前言用罗马数字（i, ii, iii），正文从第1页开始。如果书签中的页码指的是印刷页码但 offset 错位，检查 PDF 的前几页是否是非正文内容，调整罗马数字页的偏移量。

### 步骤⑤：上传与直链

**症状：** 上传返回 401/403。

认证凭证过期或格式不对。如果服务用 Bearer Token，确认 `UPLOAD_TOKEN` 值完整。如果服务用 Cookie 认证，Cookie 通常只有几小时有效期，需要重新登录获取。

**症状：** 直链生成后外网打不开。

内网穿透隧道可能离线。检查 cpolar/frp 进程：`ps aux | grep cpolar`。如果隧道在线但直链仍不可达，可能是 cpolar 免费隧道的域名发生了变化（免费版域名不固定）。

### 通用调试方法

如果以上都不适用，按以下顺序定位：

1. **确认基础设施存活。** 逐个检查：数据库、下载管理器、上传服务、代理。用 `curl` 测试每个端点的可达性。
2. **检查网络路径。** Agent 运行在 Docker/沙盒中时，`localhost` 指向容器自身而非宿主机。需改用 `host.docker.internal` 或宿主机实际 IP。
3. **核对环境变量。** `env | grep -E 'DOWNLOAD|UPLOAD'` 查看相关变量是否已设置且值正确。
4. **用已知可用输入复现。** 用一个确定在 Anna's Archive 上存在的 ISBN 跑完整管道，排除特定图书导致的问题。
5. **查看 SKILL.md 中各步骤的「失败处理」章节。** 每个步骤都有详细的错误场景和处置方案。

---

## 版本历史

| 版本 | 关键更新 |
|------|---------|
| **v15.1** | 🔴 Ghostscript 彻底移除（证实摧毁 OCR 文字层）；🟢 书签层级推断引擎 + 规范文件命名；📝 发布为通用参考架构 |
| v14 | 🔴 OCR 乱码防御（`is_ocr_readable()` + 强制 `--jobs 1`） |
| v13 | 🔴 ISBN 检索模式 + 判空保护；🟢 qpdf 后处理压缩；书签降级简化 |
| v12 | 🔴 PaddleOCR 3.2.0 兼容性修复 |
| v8 | 🔴 缓存变量名遮蔽 Bug 修复；Tesseract 移除 |

---

## 贡献

这是一个**参考架构**，不是代码库。欢迎以下形式的贡献：

- **适配案例**：把你的环境接进来后，提交 PR 补充「适配备忘」表格
- **Bug 报告**：如果你在他的环境中复现了 OCR 乱码等问题，提 Issue
- **改进 SKILL.md**：让它作为 Agent 指令更准确、更少歧义

## 许可

MIT
