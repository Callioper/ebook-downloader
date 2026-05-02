# Agent Ebook Downloader

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

全自动电子书下载与处理工具 — 输入书名或 ISBN，输出带书签的可搜索 PDF。

## 功能

### 检索
- **本地 SQLite 数据库** — 读取 `DX_2.0-5.0.db` / `DX_6.0.db`，支持书名/作者/ISBN/SS 码模糊搜索
- **NLC 元数据补全** — 自动从国家图书馆补全书目信息
- **书葵网书签提取** — 自动获取目录结构用于 PDF 书签

### 下载
- **FlareSolverr Cloudflare 绕过** — 自动解决 DDoS-Guard / Cloudflare 验证
- **Anna's Archive 会员高速** — 会员 Key 直链下载
- **Z-Library eAPI** — 邮箱密码自动登录下载
- **IPFS 网关** — 公网 IPFS 网关下载
- **aria2c BitTorrent** — DHT 自动发现种子

### 后处理管道
```
检索 → 下载 PDF → OCR 识别 → PDF 压缩 → 书签注入 → 生成报告
```
- **OCR** — 支持 Tesseract / PaddleOCR / EasyOCR / AppleOCR
- **压缩** — qpdf 结构级压缩
- **书签** — 书葵网层级目录自动注入
- **报告** — 含下载直链（内网 + 外网）的完整执行报告

## 快速开始

### 环境要求

| 组件 | 最低版本 |
|------|---------|
| Windows | 10/11 x64 |
| Python | 3.10+ |
| Node.js | 18+（仅前端开发构建需要） |
| FlareSolverr | 可选，自动下载需配置 |
| qpdf | 可选，PDF 压缩 |
| ocrmypdf | 可选，OCR 识别 |

### 使用方式

**方式一：exe 直接运行**
```bash
AgentEbookDownloader.exe
# 自动打开浏览器 → http://localhost:8000
```

**方式二：源码运行**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 命令行参数

```bash
# 不自动打开浏览器
AgentEbookDownloader.exe --no-browser

# 仅 API 服务（无 GUI）
python main.py --no-gui
```

## 配置

打开 `http://localhost:8000` → 右上角「设置」：

| 配置项 | 说明 |
|--------|------|
| SQLite 数据库目录 | 指向含 `DX_*.db` 的目录 |
| 下载目录 / 保存目录 | PDF 临时和最终存放位置 |
| HTTP 代理 | 访问外网的代理地址 |
| Anna's Archive 会员 Key | 高速下载（可选） |
| Z-Library 邮箱/密码 | Z-Library 下载（可选） |
| OCR 引擎 | 选择引擎并一键安装 |

## API

启动后访问交互式 API 文档：

- **Swagger UI** — http://localhost:8000/docs
- **ReDoc** — http://localhost:8000/redoc

主要端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/search` | GET | 基础/高级检索（支持 AND/OR 多条件） |
| `/api/v1/tasks` | POST | 创建下载任务 |
| `/api/v1/tasks/{id}` | GET | 查询任务状态和报告 |
| `/api/v1/config` | GET/POST | 读写配置 |
| `/ws/tasks/{id}` | WebSocket | 实时进度推送 |

## 技术架构

```
frontend (React 18 + TypeScript + Tailwind CSS)
backend (Python FastAPI + SQLite)
├── engine/             # 下载管道引擎
│   ├── pipeline.py         # 6 步处理管道
│   ├── flaresolverr.py     # Cloudflare 自动绕过
│   └── zlib_downloader.py  # Z-Library 下载
├── api/                # REST API 端点
├── nlc/                # NLC 书目信息爬虫
└── config.py           # 应用配置
```

## 依赖项目

- [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) ^22.2.0 — Cloudflare 绕过
- [aria2c](https://github.com/aria2/aria2) ^1.37 — BitTorrent 下载引擎
- [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF) ^17.0 — PDF 文字识别
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) ^3.2 — 中文 OCR
- [qpdf](https://github.com/qpdf/qpdf) ^11.0 — PDF 结构压缩

## License

MIT
