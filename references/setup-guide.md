# 功能选配引导

当用户说「配置 ebook-downloader」「设置 ebook-downloader」「初始化 ebook 管道」「引导我完成功能选配」或「setup ebook downloader」时，Agent 应按以下流程逐项引导用户完成功能选配。

核心原则：每项给用户三个选项——「有」（标准接入）、「自定义」（自由输入值）、「跳过」（暂不配置）。逐项询问，不要一次性抛出所有问题。每项先简要说明作用，再给选项。

---

## 引导流程

Agent 按顺序逐项询问。每项开始先说一句作用说明，然后给出三个选项，等待用户选择后再推进。每项选择「自定义」时，让用户自由输入值并原样写入 config.yaml。

---

### 第 1 项：图书元数据来源（步骤①，核心）

**作用：** 根据书名/ISBN/SS码检索图书的作者、出版社、内容提要等信息。项目地址：https://github.com/Hellohistory/EbookDatabase

**询问：** 「你有 EbookDatabase 吗？请选择：有 / 自定义 / 跳过」

**有：** 询问数据库的 HTTP API 地址（默认 `http://127.0.0.1:10223`），记录为 `ebookdb.url`。

**自定义：** 让用户直接输入任意配置值，原样写入 `config.yaml` 的 `ebookdb` 段。参考结构：
```yaml
ebookdb:
  url: "<用户输入>"
```

**跳过：** 标记此项未配置。管道中步骤① 降级为纯 Anna's Archive 搜索，会丢失 NLC 元数据校验和书葵网书签。降级影响只在当前管道中生效，不写入 config.yaml。

---

### 第 2 项：下载管理器与代理（步骤②，核心）

**作用：** 接收 Anna's Archive 的 MD5 哈希，下载 PDF 文件。内置 FlareSolverr 反爬虫。你的网络环境决定了是否需要代理。

**询问：** 「你有下载管理器（如 stacks）吗？请选择：有 / 自定义 / 跳过」

**有：** 问两个子项：

a) stacks 地址（默认 `http://127.0.0.1:7788`）和 Admin API Key。记录为 `download_manager.url` 和 `download_manager.api_key`。

b) 「你在国内需要代理访问外网吗？（是 / 否）」如果是，问代理地址（默认 `http://127.0.0.1:7890`），记录为 `proxy.http` 和 `proxy.https`。

**自定义：** 让用户自由输入 stacks 地址、API Key、代理地址，原样写入 `config.yaml`：
```yaml
download_manager:
  url: "<用户输入>"
  api_key: "<用户输入>"

proxy:
  http: "<用户输入的代理地址或留空>"
  https: "<用户输入的代理地址或留空>"
  no_proxy: "127.0.0.1,localhost"
```

**跳过：** 标记此项未配置。管道中步骤② 尝试直接用 curl 从 Anna's Archive 下载，不经过 stacks。跳过代理配置。不写入 config.yaml。

---

### 第 3 项：OCR 引擎（步骤③，核心）

**作用：** 将扫描件 PDF 转为可搜索 PDF（含文字层）。推荐 ocrmypdf + PaddleOCR，CPU 可运行。备选 MinerU（GPU，高精度版面分析）。

**询问：** 「需要 OCR 功能吗？请选择：需要 / 自定义 / 跳过」

**需要：** 推荐 ocrmypdf + PaddleOCR，询问是否启用 MinerU 高精度模式（需要 GPU）。记录 OCR 方案选择。

如果启用 MinerU，询问 WebUI 地址（默认 `http://127.0.0.1:7860`）和 API 地址（默认 `http://127.0.0.1:8000`）。记录为 `mineru.enabled`、`mineru.webui_url`、`mineru.api_url`。

同时提醒注意事项：`--jobs 1` 是强制的（多线程会乱码）；大 PDF 建议分批 OCR。

**自定义：** 用户自由输入 OCR 相关配置：
```yaml
mineru:
  enabled: <true/false>
  webui_url: "<用户输入或留空>"
  api_url: "<用户输入或留空>"
```

**跳过：** OCR 步骤被跳过。管道中如果 PDF 本身已有文字层会自动检测并跳过；扫描件 PDF 将保持无文字层状态。不写入 config.yaml。

---

### 第 4 项：书签注入（步骤④，可选）

**作用：** 将图书目录注入 PDF 书签。完整模式需要书葵网（搭配 EbookDatabase）获取多级目录（如"第一章 → 第一节"三层嵌套）；降级模式只添加一条指向目录页的书签。

**询问：** 「需要书签注入功能吗？请选择：需要 / 自定义 / 跳过」

**需要：** 再问「完整模式还是降级模式？」

完整模式：需要 EbookDatabase 和书葵网可访问，依赖 `pymupdf` 和 `pikepdf`。记录书签模式为 `full`。

降级模式：`scripts/inject_bookmarks.py --toc-only` 即可，无需外部数据源。记录书签模式为 `toc_only`。

**自定义：** 用户自由输入书签相关参数（如自定义注入脚本路径、默认 offset 等），原样写入 config.yaml。参考结构：
```yaml
bookmark:
  mode: "<full / toc_only>"
  inject_script: "<用户自定义路径或留空>"
  default_offset: <数字或留空>
```

**跳过：** 书签注入步骤被跳过。最终 PDF 不含书签。不写入 config.yaml。

---

### 第 5 项：上传与分享（步骤⑤，可选）

**作用：** 将处理好的 PDF 上传到文件存储，生成分享直链。支持 Z-File、任意 WebDAV、S3 兼容存储等。

**询问：** 「需要上传和分享功能吗？请选择：需要 / 自定义 / 跳过」

**需要：** 推荐 Z-File 网盘（Docker），询问上传地址和认证凭据。记录 `upload.url` 和 `upload.token`（或 `upload.cookie`）。

备选方案：Python http.server 临时分享、WebDAV、S3、Nextcloud。如果用户想用非推荐方案，引导用户进入「自定义」选项。

**自定义：** 用户自由输入上传服务信息：
```yaml
upload:
  url: "<用户输入>"
  token: "<用户输入或留空>"
  cookie: "<用户输入或留空>"
```

输入 token 和 cookie 二选一，留空的一项不写入。同时用户可以自由添加任意自定义字段。

**跳过：** 不上传。管道完成后只输出本地文件路径。不写入 config.yaml。

---

### 第 6 项：通知通道（步骤⑥，可选）

**作用：** 管道完成后发送结构化报告到指定渠道。支持 QQ Bot、Telegram Bot、飞书 Webhook、企业微信 Webhook。

**询问：** 「需要完成通知吗？请选择：需要 / 自定义 / 跳过」

**需要：** 问「用什么渠道？qqbot / telegram / feishu」。根据选择逐项录入：

| 渠道 | 需录入字段 |
|------|-----------|
| qqbot | `app_id`、`token`、`channel_id` |
| telegram | `bot_token`、`chat_id` |
| feishu | `webhook_url` |

记录为 `notify.enabled: true`，`notify.channel`，以及对应渠道的字段。

**自定义：** 用户自由输入通知配置：
```yaml
notify:
  enabled: true
  channel: "<用户输入>"
  <channel>:
    <key1>: "<用户输入>"
    <key2>: "<用户输入>"
```

用户可以输入任意渠道和任意字段，原样写入 config.yaml。

**跳过：** 不发送通知。报告输出到终端。不写入 config.yaml。

---

## 选配完成

全部 6 项询问完毕后，Agent 输出一份汇总，包含已选配和跳过的功能清单、需要安装的软件列表（标注哪些尚未安装），以及一份可直接保存的 config.yaml 配置内容。

**汇总模板：**

```
ebook-downloader 功能选配汇总
────────────────────────────────────────
  ① 元数据来源:  已配置 / 已跳过
  ② 下载管理器:  已配置 / 已跳过
  ③ OCR:         已配置 / 已跳过
  ④ 书签注入:    已配置 / 已跳过
  ⑤ 上传分享:    已配置 / 已跳过
  ⑥ 通知渠道:    已配置 / 已跳过
────────────────────────────────────────
  待安装软件: <列表，如无则写"无">
```

最后提示用户：「把上面的配置保存到 skill 目录下的 `config.yaml` 文件中（即 `~/ebook-downloader/config.yaml`）。配置完成后，用 `python3 scripts/config_reader.py` 确认状态，然后对我说『下载 《书名》』即可开始使用。建议先用一本确定在 Anna's Archive 上存在的书测试管道是否正常。」

**迁移说明**：如果此前使用环境变量版本，只需将对应值填入 `config.yaml` 即可。运行 `python3 scripts/config_reader.py` 可查看当前配置状态。

---

## 使用指南

选配完成后，Agent 应输出以下使用说明供用户参考。

**启动下载：**

- 「下载 《书名》」— 触发完整 7 步管道
- 「下载 ISBN 978-7-100-12345-6」— 按 ISBN 精确检索
- 「下载 SS 码 12345678」— 按读秀码检索

**单步操作（不跑全管道）：**

- 「给这个 PDF 做 OCR」— 仅对已有 PDF 执行文字层识别
- 「给这本 PDF 加书签」— 仅注入目录页书签（降级A）
- 「压缩这个 PDF」— 用 `ocrmypdf --optimize 1` 缩小体积

**首次测试建议：**

用一本确定在 Anna's Archive 上存在的中文扫描件 PDF 测试全管道，例如 ISBN 978-7-100-12345-6（仅为格式示例，请替换为你确认存在的 ISBN）。这样可以在最小变量下验证搜索、下载、OCR、书签全流程。

**预期输出：**

每次下载完成后，Agent 输出一份结构化报告，包含书名、作者、文件大小、OCR 状态（已有文字层 / 新 OCR / 跳过）、书签来源（书葵网完整目录 / 降级A目录页 / 降级B AI Vision）、本地路径和分享直链（如启用上传）。
