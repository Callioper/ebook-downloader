# Ebook Downloader — Agent Skill

一个 **6 步骤电子书下载自动化管道**。从书名/ISBN/SS 码出发，输出带 OCR 文字层和多级书签的 PDF + 分享直链。核心的搜索→下载→OCR 三步闭环不需要任何本地服务即可跑通（见 `references/evaluation-cases.md` 的零基础设施路径）。书签注入和上传分享为可选增强功能。

> 首次使用对 Agent 说「配置 ebook-downloader」，Agent 会逐项询问你的环境情况并输出定制化安装方案。

---

## 快速开始

**最简单的方式：把下面这段话原样发给你的 AI Agent。**

> 帮我安装 ebook-downloader。仓库地址：https://github.com/Callioper/ebook-downloader
>
> 1. 把整个仓库 clone 到你能读取的 skills 目录——不只要 SKILL.md，scripts/ 和 references/ 也要。
> 2. 装完运行 `python3 scripts/parse_bookmark_hierarchy.py`，确认能输出测试结果。
> 3. 引导我完成功能选配：逐项问数据库、下载管理器、OCR、书签、上传、通知——每项只问一遍，有就给对接命令，没有就给降级方案。
> 4. 输出环境变量模板和使用指南（包含启动下载、单步操作、首次测试、预期输出的示例），让我保存。

**用命令行安装（支持 skills 的 Agent）：**

```bash
npx skills add Callioper/ebook-downloader
```

适用于 Claude Code、Codex、Cursor、Windsurf 等 50+ 种 Agent。手动安装的话，`git clone https://github.com/Callioper/ebook-downloader` 到你的 skills 目录即可。

**验证安装：** 运行 `python3 scripts/parse_bookmark_hierarchy.py` 输出 4 组测试，确认 scripts/ 完整。再对 Agent 说「列出 ebook-downloader 的步骤」，应输出 6 步管道。

### 安装故障快速排查

`npx skills: command not found` 意味着 Node.js 版本太低（需要 ≥ 18），运行 `node --version` 确认后升级即可。`git clone` 权限拒绝说明仓库地址不对或用了 SSH 但没配 key，确认 https://github.com/Callioper/ebook-downloader 在浏览器能打开，改用 HTTPS 地址。Agent 不识别 skill 通常是因为 SKILL.md 没放在正确的目录——去看 `npx skills list` 或手动检查文件路径。GitHub 克隆超时的话可以先 `git clone` 到本地再 `npx skills add ./local-path` 安装。

---

## 仓库文件结构

```
ebook-downloader/
├── SKILL.md                          # 核心：Agent 加载的指令文件（6步骤 + I/O契约 + 失败策略）
├── README.md                         # 本文件：安装/配置/排错指南
├── scripts/
│   ├── parse_bookmark_hierarchy.py   # 书签层级推断引擎（栈深度模型，4种嵌套模式）
│   └── inject_bookmarks.py           # 书签注入引擎（偏移计算 + 分段检测 + 注入后验证）
└── references/
    ├── evaluation-cases.md           # 评测用例 + 最小可跑路径 + 自检清单
    ├── report-template.md            # 步骤6 结构化报告模板（成功/失败两套格式）
    ├── setup-guide.md                # 功能选配引导（6项逐项询问 → 环境变量模板）
    ├── bookmark-troubleshooting.md   # 书签问题自助手册（7种场景排查）
    ├── download-troubleshooting.md   # 下载错误分类（临时/永久）与常见场景排查
    └── ghostscript-ocr-corruption.md # Ghostscript 摧毁 OCR 文字层实证
```

`SKILL.md` 是 Agent 真正读取的指令文件，包含 6 步管道的完整定义——每步的命令、I/O 契约、失败处理方案。Agent 加载它后就知道如何编排整个下载流程。

`scripts/` 下两个 Python 脚本可独立运行：`parse_bookmark_hierarchy.py` 无参数执行输出 4 组内置测试结果，`inject_bookmarks.py` 是完整的书签注入管线（支持 `--offset`、`--ocr`、`--toc-only` 三种模式）。

`references/` 下六个参考文件按用途分三类。部署相关：`evaluation-cases.md`（零基础设施可跑路径 + 7 个评测用例）、`setup-guide.md`（6 项逐项选配引导）。排查相关：`bookmark-troubleshooting.md`（书签 7 种场景）、`download-troubleshooting.md`（错误分类与常见场景）、`ghostscript-ocr-corruption.md`（GS 摧毁文字层实证）。格式相关：`report-template.md`（成功/失败两套汇报模板）。

首次部署建议从 `evaluation-cases.md` 的零基础设施路径开始，然后跑 `setup-guide.md` 的选配引导。

---

## 这个 Skill 做什么

Agent 加载此 skill 后，说「下载 《书名》」「检索并下载 ISBN xxx」或「用 SS 码 xxx 下载」都会触发以下管道：

```
用户说「下载 《形而上学的巴别塔》」
    │
    ▼
┌─────────────────┐
│ ① 检索元数据     │  本地 DB 模糊搜索 → NLC 校验 → 书葵网取书签
│ 输出：书名/ISBN/ │  无数据库时降级为纯 Anna's Archive 搜索
│ SS码/书签文本     │
└────────┬────────┘
         ▼
┌─────────────────┐
│ ② 下载 PDF       │  Anna's Archive 搜 MD5 → stacks 下载管理器排队
│ 输出：本地 PDF    │  无 stacks 时尝试 curl 直链下载
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③ OCR            │  ocrmypdf + PaddleOCR（--jobs 1 防乱码）
│ 输出：可搜索 PDF  │  后验证 CJK 文字比率（已有文字层则跳过）
└────────┬────────┘
         ▼
┌─────────────────┐
│ ④ 生成书签       │  书葵网书签优先 → 降级A（仅目录页）→ 降级B（AI Vision）
│ 输出：带书签 PDF  │  脚本：scripts/inject_bookmarks.py
└────────┬────────┘
         ▼
┌─────────────────┐        ┌─────────────────┐
│ ⑤ 上传 + 直链    │        │ ⑥ 生成报告       │
│ 可选：无后端则跳过 │   →   │ 参照 report-     │
│ Z-File / S3 等   │        │ template.md     │
└─────────────────┘        └─────────────────┘
```

---

## 前置依赖

### 你必须自建的基础设施

| 步骤 | 需要什么 | 推荐方案 |
|------|---------|---------|
| ① 检索 | 图书元数据来源 | [EbookDatabase](https://github.com/Hellohistory/EbookDatabase) Docker 或本地 SQLite + [NLC 联合编目 API](http://opac.nlc.cn) |
| ① 检索 | 书签数据源 | [书葵网 shukui.net](https://shukui.net) 爬虫 |
| ② 下载 | 下载管理器 | [stacks](https://github.com/annas-archive/stacks) Docker（含 FlareSolverr）或自建队列 |
| ② 下载 | 外网代理（中国大陆） | Clash/V2Ray（127.0.0.1:7890） |
| ③ OCR | ocrmypdf | `pip install ocrmypdf ocrmypdf-paddleocr` |
| ③ OCR | PaddleOCR | `pip install paddlepaddle paddleocr` |
| ③ OCR | PDF 文字层检测 | `pip install PyMuPDF`（`import fitz`） |
| ④ 书签 | 书签注入 | `pip install pikepdf PyMuPDF` |
| ④ 书签 | 层级推断 | 本仓库自带 `scripts/parse_bookmark_hierarchy.py`（纯 Python，无外部依赖） |
| ④ 书签 | 图片转换（PDG→PDF） | `pip install Pillow` |
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

---

## 核心发现

几个在实战中验证过的关键结论，避免踩坑：EbookDatabase 的 `second_pass_code` 不是 Anna's Archive 可用的 MD5 格式，下载必须从 Anna's Archive 搜索页直接提取 32 位十六进制 MD5。PaddleOCR 在多线程下（`--jobs > 1`）会 100% 静默产生乱码，强制 `--jobs 1` 是 OCR 命令里最重要的一行。Ghostscript 的 `pdfwrite` 会彻底摧毁 CJK 文字层——207 页中文 PDF 实测全部 CJK=0，完整实证见 `references/ghostscript-ocr-corruption.md`，压缩只能用 `ocrmypdf --optimize 1` 或 `qpdf --recompress-flate`。书葵网书签是扁平文本没有缩进，必须用命名规则推断层级（"第X部分 > 第X章 > 第X节 > 一、"），旧的 Tab 缩进法完全无效。

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

正常现象。管道会自动检测文件类型——zip 内是单文件 PDF 则自动提取并重命名为 `.pdf`，zip 内是 PDG/JPG 图片组则自动合成为 PDF。如果自动检测失败，手动用 `file downloaded.zip` 查看真实类型，用 `unzip -l downloaded.zip` 查看内容。详细错误分类与常见场景见 `references/download-troubleshooting.md`。

### 步骤③：OCR

**症状：** OCR 后中文文字层全是乱码/空白。

这是最常见的 OCR 问题。99% 的情况是因为 `--jobs` 参数 > 1。PaddleOCR 在多线程下存在编码损坏的 bug，强制使用 `--jobs 1`。

如果已经用了 `--jobs 1` 但仍然乱码，检查 PaddleOCR 版本。3.0+ 的 `predict()` 返回值格式有变化，需要确认 ocrmypdf-paddleocr 插件是否兼容。可以降级到 PaddleOCR 2.8.x 试试。

**症状：** OCR 进程被 kill（OOM）。

大 PDF（>500 页）OCR 时内存消耗大。解决方案：用 `--pages 1-50`、`--pages 51-100` 等分批 OCR，最后用 pikepdf 合并。每批 50 页是一个安全的值。

**症状：** 报 `KeyError: 'text_word_region'` 或 `ZeroDivisionError`。

前者是 PaddleOCR 2.9.1+ 的 `return_word_box=True` API 变化，需要 patch `ocrmypdf_paddleocr/engine.py`。后者是部分 PDF 元数据 DPI=0 导致的，ocrmypdf 新版已内置补丁，升级到最新版即可。WSL2 用户还要注意 `/tmp` 目录可能被 systemd 自动清理——改用固定目录如 `~/tmp/ocrmypdf`。关于 Ghostscript 摧毁 OCR 文字层的完整实证，见 `references/ghostscript-ocr-corruption.md`。

### 步骤④：书签注入

**症状：** pikepdf 报 `PdfError` 或权限错误。

PDF 可能设置了所有者密码（即使打开不需要密码）。用 `qpdf --decrypt input.pdf output.pdf` 移除限制后重试。注意这不能破解用户密码，只能移除编辑/打印限制。

**症状：** 注入的书签页码对不上。

PDF 的「逻辑页码」和「物理页码」可能不一致。比如封面、目录、前言用罗马数字（i, ii, iii），正文从第1页开始。如果书签中的页码指的是印刷页码但 offset 错位，检查 PDF 的前几页是否是非正文内容，调整罗马数字页的偏移量。完整排查指南见 `references/bookmark-troubleshooting.md`，覆盖 7 种常见失败场景。

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

此 skill 最初在 Hermes Agent + WSL2 环境中为中文学术图书下载开发，历经多个大版本迭代。关键里程碑包括：PaddleOCR 3.2.0 兼容性修复（v12）、ISBN 检索模式与判空保护（v13）、OCR 乱码防御机制的建立（v14，发现 `--jobs > 1` 100% 产生乱码）、Ghostscript 的彻底移除（v15.1，实证 `pdfwrite` 摧毁 CJK 文字层）、书签层级推断引擎的引入。v15.1 起作为通用参考架构公开发布。

## 贡献

这是一个参考架构，欢迎提交适配案例到适配备忘表格、报告你环境中复现的问题、或改进 SKILL.md 让它作为 Agent 指令更准确。

## 许可

MIT