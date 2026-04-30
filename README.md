# Ebook Downloader — Agent Skill

一个 **7 步骤电子书下载自动化管道**的通用参考架构。从书名/ISBN 到可搜索 PDF + 书签 + 分享链接，全自动。

> ⚠️ **这不是开箱即用的工具。** 它是一个架构蓝图——你需要用自己的基础设施替换每个步骤。详见 [适配备忘](#适配备忘)。

## 安装

```bash
# 安装此 skill 到你的 AI Agent
npx skills add Callioper/ebook-downloader

# 或指定目标 Agent
npx skills add Callioper/ebook-downloader -a claude-code -a opencode
```

支持的 Agent：Claude Code、Codex、Cursor、OpenCode、Windsurf 等 50+ 种。

## 管道概览

```
书名/ISBN/SS码
    │
    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ ① 检索元数据 │ → │ ② 下载 PDF   │ → │ ③ OCR       │
│ 本地DB+NLC+  │    │ Anna's       │    │ ocrmypdf+   │
│ 书葵网       │    │ Archive+下载 │    │ PaddleOCR   │
└──────────────┘    │ 管理器       │    └──────────────┘
                     └──────────────┘           │
                                                ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ ⑥ 生成报告   │ ← │ ⑤ 上传+直链 │ ← │ ④ 生成书签   │
│ 结构化       │    │ Z-File/S3/  │    │ 三级降级策略 │
│ Telegram/等  │    │ WebDAV      │    │ 层级推断引擎 │
└──────────────┘    └──────────────┘    └──────────────┘
                          ↑
                    ┌──────────────┐
                    │ ③.5 压缩    │
                    │ qpdf(安全)   │
                    │ ⛔非GS       │
                    └──────────────┘
```

## 核心亮点

- **OCR 乱码防御**：发现并修复了 `ocrmypdf --jobs > 1` 在 PaddleOCR 下 100% 静默产生乱码的 bug
- **Ghostscript 陷阱**：实证分析证实 `pdfwrite` 会完全摧毁 CJK 文字层
- **MD5 溯源**：揭示了 EbookDatabase `second_pass_code` 与 Anna's Archive 真实 MD5 的结构差异
- **书签层级推断**：栈深度模型自动还原扁平书签为多级嵌套树
- **三级降级**：正常注入 → 仅目录页 → AI Vision 提取

## 适配备忘

| 原版组件 | 你需要替换为 |
|---------|------------|
| 本地图书数据库 | 你的元数据来源 |
| Docker 下载管理器 | 自建下载队列或直连 Anna's Archive |
| 书葵网书签爬虫 | 你的书签来源 |
| 自托管 Z-File 网盘 | S3 / Nextcloud / WebDAV |
| 内网穿透隧道 | Cloudflare Tunnel / frp |

## 开发背景

此 skill 最初在 **Hermes Agent + WSL2** 环境中为中文学术图书下载开发，历经 v8→v15.1 共 8 个大版本迭代，修复了 PaddleOCR 兼容性、缓存变量名遮蔽、代理路由、文件类型自动检测等数十个实际生产问题。

发布此通用版本是为了让其他开发者复用架构设计和故障排除经验。

## 许可

MIT
