# Book Downloader

全自动电子书下载与处理工具。集成 SQLite 本地检索、Anna's Archive 会员高速下载、FlareSolverr Cloudflare 绕过、Z-Library 搜索下载，以及完整的 6 步后处理管道。

## 功能

### 检索
- **本地 SQLite 数据库** — 直接读取 `DX_2.0-5.0.db` / `DX_6.0.db`，支持书名/作者/ISBN/SS码模糊搜索
- **外部书源回退** — 本地无结果时自动搜索 Anna's Archive + Z-Library，显示完整元数据

### 下载
- **FlareSolverr 自动绕过** — 自动解决 Cloudflare/DDoS-Guard 验证
- **Anna's Archive 会员高速** — 会员 Key 直链下载
- **Z-Library eAPI** — 邮箱密码自动登录，支持搜索和下载
- **IPFS 网关** — 通过公网 IPFS 网关下载
- **aria2c BitTorrent** — DHT 自动发现种子

### 处理管道
1. **检索信息** — NLC 数据库补全书目信息、书葵网目录提取
2. **下载 PDF** — 多源自动下载
3. **OCR 文字识别** — 支持 Tesseract / PaddleOCR / EasyOCR / AppleOCR
4. **PDF 压缩** — 减小文件体积
5. **保存到本地** — 自动整理到完成目录
6. **生成报告** — 完整的下载执行报告

## 快速开始

### 环境要求
- Windows 10/11 (x64)
- Python 3.10+ (如需从源码运行)
- FlareSolverr (可选，自动下载需配置)

### 使用方式

**方式一：exe 直接运行**
```
双击 BookDownloader.exe → 自动打开浏览器 → http://localhost:8000
```

**方式二：源码运行**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 配置说明

打开 http://localhost:8000 → 右上角「设置」：

| 配置项 | 说明 |
|--------|------|
| SQLite 数据库目录 | 指向含 `DX_2.0-5.0.db` 的目录 |
| 下载目录 / 保存目录 | PDF 临时和最终存放位置 |
| HTTP 代理 | 访问外网所需的代理地址 |
| Anna's Archive 会员 Key | 高速下载（可选） |
| Z-Library 邮箱/密码 | Z-Library 自动下载 |
| OCR 引擎 | 选择文字识别引擎并一键安装 |

### 命令行参数

```
# 启动时不自动打开浏览器
BookDownloader.exe --no-browser

# 仅启动 API 服务（无 GUI）
python main.py --no-gui
```

## 技术架构

```
frontend (React + TypeScript + Tailwind)
backend (Python FastAPI + SQLite)
├── engine/          # 下载管道引擎
│   ├── pipeline.py      # 6 步处理管道
│   ├── flaresolverr.py  # Cloudflare 自动绕过
│   └── zlib_downloader.py # Z-Library 下载
├── api/             # REST API 端点
├── nlc/             # NLC 书目信息爬虫
└── config.py        # 应用配置
```

## 依赖项目

- [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) — Cloudflare 绕过
- [aria2c](https://github.com/aria2/aria2) — BitTorrent 下载引擎
- [ocrmypdf](https://github.com/ocrmypdf/OCRmyPDF) — PDF 文字识别
- [zlibrary](https://github.com/bipinkrish/Zlibrary-API) — Z-Library API 参考

## License

MIT