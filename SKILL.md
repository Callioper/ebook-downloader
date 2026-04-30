---
name: ebook-downloader
description: 7步骤电子书下载通用参考架构 — 从书名/ISBN到可搜索PDF+书签+直链的全自动管道。可作为构建自托管图书下载Agent的蓝图。
---

# Ebook Downloader — 通用参考架构

> **这是什么？** 一个 7 步骤的电子书下载自动化管道参考实现。你无法直接使用它（因为它依赖你自建的基础设施），但你可以把它当作**架构蓝图**，用自己的工具栈替换每个步骤。
>
> **原版背景：** 此 skill 最初在 Hermes Agent + WSL2 环境中开发，用于自动化中文学术图书下载（含 OCR + 书签注入）。本版本剥离了 Hermes 专有依赖，改为通用参考。

---

## 触发条件（Agent 必读）

**Use this skill when（正向触发）：**

- 用户说「下载 《书名》」「帮我找 《书名》」
- 用户输入 ISBN（如 `978-7-100-12345-6`）要求检索并下载
- 用户输入 SS 码（读秀码）要求下载对应图书
- 用户请求完整的「检索→下载→OCR→书签→上传」管道
- 用户只要求单步操作但该步骤在本 skill 中有定义（如「给这个 PDF 做 OCR」「给这本 PDF 加书签」）

**Do NOT use this skill when（负向触发）：**

- 用户只是查询图书元数据（书名/作者/出版社），不需要下载——此时只需要元数据检索，不走完整管道
- 用户上传了一个 PDF 只要求「压缩」或「格式转换」——这些是独立的 PDF 处理任务，非图书下载
- 用户问「之前的下载任务完成了吗？」——这是状态查询，不是新任务
- 图书已在本地有完整文件，用户只需要上传或分享——跳过下载和 OCR 步骤
- 用户输入的是论文标题/期刊文章而非图书——这需要不同的检索策略

---

## 管道 I/O 契约

Agent 在执行此 skill 时，应维护以下跨步骤状态对象。每个步骤的输入来自上一步的输出。

**管道输入：** 用户提供的 `book_name`（字符串）、`isbn`（字符串）或 `ss_code`（字符串），三者至少提供一个。

**管道输出：** 一份结构化完成报告，包含：书名、作者、文件大小、OCR 状态、书签来源、分享直链。

**跨步骤状态对象：**

`pipeline_state` 字典在各步骤间传递，包含以下字段：

- `candidates` — 步骤1输出的候选图书列表。每个候选项含 `title`、`isbn`、`ss_code`、`authors`、`publisher`、`nlc_comments`、`nlc_tags`、`bookmark`（可为 null）。取 `candidates[0]` 作为主候选。
- `pdf_path` — 步骤2输出、步骤3输入、步骤4输入、步骤5输入的本地 PDF 绝对路径。是管道中最关键的传递变量。
- `expected_meta` — 步骤1输出的元数据快照（`title`、`authors`、`publisher`、`isbn`），步骤5上传时用于核对文件名与内容是否一致。
- `bookmark` — 步骤1从书葵网获取的原始书签文本，步骤4用于注入 PDF。为 `null` 时触发降级A。
- `steps_completed` — 已完成的步骤编号列表（如 `[1, 2, 3]`），用于步骤6汇报和故障定位。
- `errors` — 非致命错误的收集列表。每个错误记录步骤编号、错误类型、简要描述。用于步骤6汇报但不中断管道。

**步骤间 I/O 映射：**

- 步骤1 → 步骤2：`candidates[0].ss_code`（或从 Anna's Archive 搜索得到的 MD5）
- 步骤1 → 步骤4：`candidates[0].bookmark`
- 步骤1 → 步骤5：`expected_meta`（用于核对）
- 步骤2 → 步骤3：`pdf_path`
- 步骤3 → 步骤4：`pdf_path`
- 步骤4 → 步骤5：`pdf_path`

---

## 整体架构

```
用户输入 书名 / ISBN / SS码
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤 1：检索元数据                                         │
│  └─ 书名模式 → 本地数据库 / NLC 联合编目 / 书葵网          │
│  └─ ISBN模式 → Anna's Archive 直接搜 MD5                   │
│  └─ SS码模式 → 用 SS码查询本地数据库                       │
│  输出：基本信息 + ISBN + SS码 + 书签文本                    │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  步骤 2：下载 PDF（核心：Anna's Archive → 下载管理器）     │
│                                                              │
│  书名/ISBN → annas-archive.gd/search → 提取 MD5             │
│  → 下载管理器 API POST /api/queue/add                        │
│  → 轮询 /api/status 直到下载完成                            │
│                                                              │
│  输出：本地 PDF 文件路径                                    │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────┐
│  步骤 3：OCR（扫描件 PDF → 可搜索 PDF） │
│                                         │
│  ocrmypdf + PaddleOCR 插件              │
│  强制 --jobs 1（多线程会静默乱码）       │
│  输出：可搜索 PDF 路径                   │
└─────────────────┬───────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│  步骤 3.5：PDF 结构压缩（可选）          │
│                                         │
│  qpdf --recompress-flate（安全）         │
│  ⛔ 禁止 Ghostscript pdfwrite            │
│     （会彻底摧毁 OCR 文字层）            │
└─────────────────┬───────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│  步骤 4：生成书签                        │
│                                         │
│  第一优先：已获取的书葵网书签 → 注入      │
│  降级A：仅添加目录页（offset不可靠）      │
│  降级B：AI Vision 提取（用户要求时）      │
│  输出：带多级书签的 PDF                   │
└─────────────────┬───────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│  步骤 5：上传 + 生成分享链接             │
│                                         │
│  REST API 上传 → 生成直链（30天有效期）  │
│  输出：内网直链 + 外网直链               │
└─────────────────┬───────────────────────┘
                    ▼
┌─────────────────────────────────────────┐
│  步骤 6：生成完成报告                    │
│                                         │
│  结构化报告：书名/作者/大小/OCR/书签/链  │
└─────────────────────────────────────────┘
```

---

## 步骤详解

### 步骤 1：检索元数据

三种检索模式：

| 模式 | 输入 | 方法 | 输出 |
|------|------|------|------|
| 书名 | `book_name` | 本地数据库模糊搜索 + NLC 元数据校验 + 书葵网书签 | Candidate[] |
| ISBN | `isbn` | 本地数据库查找 → Anna's Archive 搜索 | Candidate[] |
| SS码 | `ss_code` | 直接用 SS码查本地数据库 | Candidate[] |

**Candidate 数据结构：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | str | 书名 |
| `isbn` | str | ISBN |
| `ss_code` | str | 读秀 SS 码 |
| `authors` | str[] | 作者列表 |
| `publisher` | str | 出版社 |
| `nlc_comments` | str | NLC 内容提要 |
| `nlc_tags` | str[] | NLC 主题词 |
| `bookmark` | str\|null | 书葵网书签文本（或多级目录） |

**可用数据源：**
- **EbookDatabase**：自建本地图书数据库（HTTP API），提供模糊搜索
- **NLC（中国国家图书馆联合编目）**：元数据校验和补充
- **书葵网（shukui.net）**：提供图书目录/书签
- **Anna's Archive**：搜索页直接提取真实 MD5

**失败处理：**

- 本地数据库不可达（连接超时/拒绝）→ 降级为纯 NLC 检索。如果 NLC 也失败，提示用户手动提供 ISBN。
- NLC 返回空结果 → 不影响管道继续，`nlc_comments` 和 `nlc_tags` 留空。用 `_fallback: true` 标记。
- 书葵网不可达 → `bookmark` 设为 `null`，步骤4 自动走降级A（仅目录页）。
- 三种模式都没结果 → 向用户报告「未找到该图书」，终止管道。不自行编造数据。

---

### 步骤 2：下载 PDF

**核心发现：EbookDatabase 的 MD5 ≠ Anna's Archive 的 MD5**

```
EbookDatabase second_pass_code 格式：
  944b8c6fc6d9076...#6cea7d57cd9e0bf5...#11440378#12928975_何为女性.zip
  └─ MD5 part1 ─┘#└─ MD5 part2 ─┘#filesize#filename

Anna's Archive 真实 MD5：
  21a20f838a2bc8a8efe5e4b1073dc1cf
  → 下载管理器可直接使用
```

**推荐流程：**

```bash
# 1. 从 Anna's Archive 搜索页提取 MD5
curl "https://annas-archive.gd/search?q={书名或ISBN}" \
  | grep -oP '/md5/[a-f0-9]{32}' \
  | head -5

# 2. 提交 MD5 到下载管理器
curl -X POST "$DOWNLOAD_MANAGER_URL/api/queue/add" \
  -H "X-API-Key: $DOWNLOAD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"md5": "21a20f838a2bc8a8efe5e4b1073dc1cf"}'

# 3. 轮询下载状态
curl -s "$DOWNLOAD_MANAGER_URL/api/status" \
  -H "Authorization: Bearer $DOWNLOAD_API_KEY"
```

> **备选方案：** 也可用 Z-Library、LibGen 等作为下载源。Anna's Archive 是首选因为它通过 MD5 直接定位文件。

**⚠️ 文件类型自动修正：**
- 扩展名 `.zip` 但内容是 `%PDF-1.4` → 重命名为 `.pdf`
- 扩展名 `.zip` 内容为 ZIP 含 PDG/JPG → 自动转换为 PDF

**失败处理：**

- Anna's Archive 不可达（DNS 解析失败/连接超时）→ 检查代理是否正常。重试最多 3 次，间隔 10 秒。3 次均失败则报告用户「Anna's Archive 当前不可用，请稍后重试」。
- 搜索返回 0 结果 → 报告用户「Anna's Archive 未收录此书」。不盲目尝试其他书名变体（容易下载到错误文件）。
- 下载管理器不可达（`localhost:7788` 拒绝连接）→ 检查 Docker 容器是否运行。如果用户未部署下载管理器，引导用户先部署 stacks。
- 下载超时（大文件）→ 不中断，继续轮询。每 2 分钟报告一次进度（已下载百分比或字节数）。
- 下载的文件损坏（MD5 不匹配/无法打开）→ 丢弃文件，标记此 MD5 无效，从候选列表中取下一个 MD5 重试。

---

### 步骤 3：OCR — ocrmypdf + PaddleOCR

**统一方案：ocrmypdf + PaddleOCR 插件**（不推荐 Tesseract，CJK 识别率低）

```bash
PYTHON=/usr/bin/python3
rm -rf /tmp/ocrmypdf.io.* 2>/dev/null
mkdir -p /tmp/ocrmypdf

# ⚠️ --jobs 1 是强制要求！>1 会静默产生乱码（PaddlePaddle 线程冲突）
TMPDIR=/tmp/ocrmypdf $PYTHON -m ocrmypdf \
  --plugin ocrmypdf_paddleocr \
  -l chi_sim+eng \
  --jobs 1 \
  --output-type pdf \
  --mode force \
  input.pdf output_ocr.pdf
```

**OCR 后验证（防止静默乱码）：**

```python
def is_ocr_readable(pdf_path, cjk_ratio_threshold=0.01):
    """检测 OCR 后 PDF 文字层是否正常（CJK 比率检测）"""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    total_chars = 0
    cjk_chars = 0
    for page in doc:
        text = page.get_text()
        total_chars += len(text)
        cjk_chars += sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    doc.close()
    cjk_ratio = cjk_chars / total_chars if total_chars > 0 else 0
    return cjk_ratio >= cjk_ratio_threshold
```

**OCR 错误速查表：**

| 错误 | 原因 | 修复 |
|------|------|------|
| `--jobs > 1` → 文字层全是乱码 | PaddlePaddle 线程冲突导致文本编码损坏 | 强制 `--jobs 1` + OCR 后用 `is_ocr_readable()` 检测 |
| `/tmp` 清理 → `FileNotFoundError` | 长进程中 `/tmp` 自动清理 | `TMPDIR=/path/to/fixed/dir` |
| DPI=0 → `ZeroDivisionError` | 部分 PDF 元数据 DPI=0 | 已打补丁 |
| `KeyError: 'text_word_region'` | PaddleOCR 2.9.1+ `return_word_box=True` API 变化 | Patch `engine.py` 3处 |

**失败处理：**

- OCR 后 `is_ocr_readable()` 检测到 CJK 比率 < 1% → 说明文字层损坏。丢弃输出文件，检查是否用了 `--jobs > 1`（最常见的根因），修正后重试一次。
- OCR 进程中途崩溃（OOM/段错误）→ 大 PDF 可能内存不足。尝试用 `--pages` 分批 OCR，每批 50 页。
- PaddleOCR 模型下载失败 → 检查网络和代理。首次运行需下载模型（约 200MB），如代理不通则手动指定模型路径。
- `TMPDIR` 目录被清理 → WSL2 环境下 `/tmp` 可能被 systemd 清理。改用固定目录如 `~/tmp/ocrmypdf`。

---

### 步骤 3.5：PDF 结构压缩

> ⛔ **绝对禁止 Ghostscript `pdfwrite`！** 实测证实它 100% 摧毁 OCR 文字层（《社会形态学》207页全部 CJK=0）

```bash
# 方案A：ocrmypdf 内置优化（安全，推荐）
ocrmypdf --optimize 1 input.pdf output.pdf

# 方案B：qpdf 结构压缩（安全，无损文字层）
qpdf --recompress-flate --object-streams=generate input.pdf output.pdf
```

---

### 步骤 4：生成书签

**三级降级策略：**

| 优先级 | 来源 | 说明 |
|--------|------|------|
| **第一** | 步骤1已获取的书葵网书签 | 直接注入 PDF |
| **降级A** | 仅添加目录页书签 | 默认行为，offset 不可靠 |
| **降级B** | AI Vision 提取 | 用户明确要求时才触发 |

**书签层级自动推断：**

书葵网书签通常是扁平列表，需解析为 PDF 树状层级：

```python
# 栈深度层级推断模型
# 识别模式：第X部分 > 第X章 > 第X节 > 一、二、... > 1. 2. ...
def parse_bookmark_hierarchy(flat_bookmarks):
    """
    输入：扁平书签行列表
    [
      "第一部分 导论",
      "第一章 开端",
      "第一节 起点",
      "一、方法论的转向",
      "第二章 展开",
      ...
    ]
    输出：多级嵌套书签树
    [
      {"title": "第一部分 导论", "level": 0, "children": [
        {"title": "第一章 开端", "level": 1, "children": [
          {"title": "第一节 起点", "level": 2, "children": [
            {"title": "一、方法论的转向", "level": 3},
          ]},
        ]},
        {"title": "第二章 展开", "level": 1},
      ]},
    ]
    """
    # 正则模式匹配 → 栈深度模型
    # 详见原版 scripts/parse_bookmark_hierarchy.py
```

**输出文件命名规范：**
```
书名_作者（YYYYMMDD）.pdf
例：纸性戀宣言_作者（20260430）.pdf
```

**失败处理：**

- 书葵网书签文本解析失败（格式异常/空内容）→ 降级A：仅添加目录页书签。不为此类数据源问题阻塞管道。
- `parse_bookmark_hierarchy()` 无法推断层级（书签格式不符合已知模式）→ 所有条目按 level=0 平级注入。在 `errors` 列表中记录「书签层级推断失败，已平铺注入」。
- PDF 元数据缺少出版年份 → 文件名中的年份用 `0000` 占位。在步骤6汇报中标注「出版年缺失」。
- pikepdf 注入报错（权限/加密 PDF）→ 如果 PDF 有密码保护且不知道密码，跳过书签注入。在 `errors` 中记录。

---

### 步骤 5：上传 + 生成分享链接

通用两步上传流程：

```bash
# Step 1: 获取预签名上传 URL
curl -s "$UPLOAD_SERVICE_URL/api/upload/presign" \
  -H "Authorization: Bearer $UPLOAD_TOKEN" \
  -d '{"filename": "book.pdf", "size": 12345678}'

# Step 2: PUT 直传文件
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @book.pdf

# Step 3: 生成分享直链（30天有效期）
curl -s "$UPLOAD_SERVICE_URL/api/share/create" \
  -H "Authorization: Bearer $UPLOAD_TOKEN" \
  -d '{"file_id": "xxx", "expire_days": 30}'
```

> 原版使用自托管 Z-File 网盘作为上传后端。你可以替换为 Nextcloud、WebDAV、S3 等任意存储。

**失败处理：**

- 上传服务不可达（连接拒绝/超时）→ 重试 3 次，间隔 5 秒。仍然失败则报告用户「上传服务不可用，PDF 已保存在本地：{pdf_path}」。
- 认证失败（401/403）→ 检查 `UPLOAD_TOKEN` 是否过期。如果是 Cookie 认证，检查 Cookie 是否过期。提示用户重新获取凭证。
- 文件过大被拒（413）→ 用 `qpdf --recompress-flate` 压缩后重试。仍然过大则分卷或放弃上传，报告文件大小。
- 预签名 URL 过期 → 重新请求预签名 URL 后立即上传。预签名 URL 有效期通常为 5-15 分钟。
- 直链生成后外网不可达 → 检查隧道工具（cpolar/frp）是否在线。只返回内网直链，标注「外网不可达，原因：隧道离线」。

---

## 适配备忘：从原版迁移到你的环境

| 原版组件 | 作用 | 你需要替换为 |
|---------|------|------------|
| EbookDatabase（本地:10223） | 图书元数据检索 | 你的本地数据库或直接调 NLC API |
| stacks Docker（本地:7788） | Anna's Archive 下载代理 | 自建下载管理器或直接 curl Anna's Archive |
| 书葵网爬虫（Python模块） | 获取书签 | 自行实现或使用其他书签源 |
| Z-File（内网:32771） | PDF 存储 + 直链 | Nextcloud / S3 / WebDAV / 任意文件存储 |
| cpolar 隧道 | 内网穿透（外网访问） | Cloudflare Tunnel / ngrok / frp |
| Hermes Agent 工具 | 编排调度 | Claude Code / Codex / Cursor 等任意 Agent |

---

## 网络注意事项

- Anna's Archive 等外网访问需要代理（如果你在中国大陆）
- 本地服务（数据库、下载管理器、存储）放在内网即可
- 外网分享通过隧道工具（Cloudflare Tunnel / frp）暴露

---

---

## 管道级失败策略

以下规则覆盖所有步骤的通用错误处理：

**重试原则：** 网络类失败（超时、连接拒绝、DNS 失败）自动重试 3 次，间隔递增（5s / 10s / 20s）。逻辑类失败（404、格式错误）不重试，直接报告。

**降级原则：** 任一步骤的非致命错误不阻塞管道。步骤3 OCR 失败 → 跳过 OCR，交付无文字层的 PDF。步骤4 书签失败 → 注入降级A。步骤5 上传失败 → 报告本地路径。每一步将错误记入 `pipeline_state.errors`，步骤6 汇总汇报。

**中断原则：** 只有以下情况立即终止管道：(1) 步骤1 完全找不到图书元数据；(2) 步骤2 所有 MD5 候选均下载失败；(3) 磁盘空间不足（< 100MB）。

**进度通知：** 长步骤（下载、OCR）每 2 分钟向用户报告进度。用户可随时说「停止」中断管道。中断时保留已完成步骤的产物。

## 通用调试方法

当管道某一步失败时，按以下顺序定位问题：

**第一步：确认基础设施存活。** 检查下载管理器是否运行（`curl localhost:7788/api/status`）。检查上传服务是否可达（`curl $UPLOAD_SERVICE_URL`）。检查代理是否通（`curl -x http://127.0.0.1:7890 https://annas-archive.gd`）。大多数管道中断的原因是某个后端服务挂了。

**第二步：检查网络路径。** Agent 所在环境能否访问外网（Anna's Archive）？能否访问内网服务（数据库、下载管理器、上传服务）？如果 Agent 在 Docker/沙盒中运行，内网 localhost 可能指向容器自身而非宿主机——需改用 `host.docker.internal` 或宿主机 IP。

**第三步：检查环境变量。** `DOWNLOAD_MANAGER_URL`、`DOWNLOAD_API_KEY`、`UPLOAD_SERVICE_URL`、`UPLOAD_TOKEN` 是否已设置且值正确？用 `env | grep -E 'DOWNLOAD|UPLOAD'` 快速核对。

**第四步：查看 `pipeline_state.errors`。** 管道中收集的非致命错误列表是定位问题的第一手材料。每个错误记录了步骤编号和类型，可以快速缩小排查范围。

**第五步：用最小输入复现。** 用一个已知可用的 ISBN（如一本常见的书）跑完整管道，排除是特定图书的问题还是管道本身的问题。

## 已知限制

- **Z-Library** 每日免费限额 10 本
- **书葵网** 主要收录古籍/学术 PDF，通俗书大概率无目录
- **NLC** 主要收录学术专著，通俗小说几乎查不到
- **Anna's Archive MD5** 是唯一可靠的下载标识符，不接受 second_pass_code 等其他格式
- **OCR 多线程乱码**：PaddleOCR + ocrmypdf 在 `--jobs > 1` 时 100% 触发

---

## 版本历史（自 v9 起的关键修复）

| 版本 | 关键更新 |
|------|---------|
| v15.1 | 🔴 Ghostscript 彻底移除（证实摧毁 OCR 文字层）；🟢 书签层级推断引擎 + 规范文件命名 |
| v14 | 🔴 OCR 乱码防御（`is_ocr_readable()` + `--jobs 1`）；📝 术语统一 5步→7步 |
| v13 | 🔴 ISBN 检索模式 + 判空保护；🟢 qpdf 后处理压缩；🔴 书签降级简化 |
| v12 | 🔴 PaddleOCR 3.2.0 兼容性修复；🟢 OCR 进度通知 |
| v8 | 🔴 Bug修复：缓存变量名不一致、Ghostscript 移除、Tesseract 移除 |

---

## 许可

MIT License — 自由使用、修改、分发。如果基于此构建了你的图书下载管道，欢迎 PR 分享你的适配经验。
