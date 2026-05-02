# Book Downloader Web — 开发方案

> 版本：v1.0 | 日期：2026-04-30 | 预计工期：4-6 天

---

## 一、项目概述

将 telegram-book-downloader 的 7 步图书下载管道从 Hermes Agent 对话式执行改造为独立 Web 服务，
提供网页端操作界面和 Windows .exe 封装。用户无需通过 Agent 对话即可完成完整的图书下载操作。

### 1.1 核心目标

| 序号 | 目标 | 优先级 |
|------|------|--------|
| 1 | 网页端基础检索 + 高级检索 | P0 |
| 2 | 7 步下载管道 Web 化执行 | P0 |
| 3 | 实时进度同步（WebSocket 推送） | P0 |
| 4 | 执行报告（含下载直链） | P0 |
| 5 | 环境配置管理（Web UI 修改） | P1 |
| 6 | Windows .exe 封装 | P1 |
| 7 | systemd 服务部署（WSL2/Linux） | P2 |

### 1.2 不做什么

- 不实现用户登录/权限系统（单用户场景）
- 不实现分布式任务队列（单机串行管道）
- 不重写管道逻辑为 Go（Python 代码直接复用）
- 不支持断点续传（V1 暂不做）

---

## 二、技术选型

### 2.1 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│                       浏览器 (React)                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ 搜索页面    │  │ 任务进度面板  │  │ 报告查看            │ │
│  │ (Tab 切换)  │  │ (WebSocket)  │  │ (HTML render)       │ │
│  └─────┬──────┘  └──────┬───────┘  └──────────┬───────────┘ │
└────────┼─────────────────┼────────────────────┼─────────────┘
         │ HTTP REST       │ WebSocket          │ HTTP REST
         ▼                 ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI 后端                           │
│                                                              │
│  /api/v1/search          → 三层检索管道                      │
│  /api/v1/tasks           → 创建/查询/取消任务                │
│  /ws/tasks/{id}          → 实时进度推送                      │
│  /api/v1/config          → 环境配置读写                      │
│  /api/v1/tasks/{id}/report → 获取执行报告                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              TaskManager (任务调度器)                  │   │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  │   │
│  │  │Step 1│→ │Step 2│→ │Step 3│→ │Step 4│→ │Step 5│  │   │
│  │  │ 检索 │  │ 下载 │  │ OCR  │  │ 书签 │  │ 上传 │  │   │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  │   │
│  │       │          │          │          │          │    │   │
│  │       ▼          ▼          ▼          ▼          ▼    │   │
│  │  ┌──────────────────────────────────────────────────┐ │   │
│  │  │      WebSocket 广播 (ws_manager)                 │ │   │
│  │  └──────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │             task_store (SQLite)                       │   │
│  │  task_id | status | pipeline_state | report | logs   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈对照

| 组件 | 选择 | 备选 | 选择理由 |
|------|------|------|---------|
| **Web 框架** | FastAPI (Python) | Go Gin | 管道代码全在 Python，直接 import 复用；原生 async + WebSocket |
| **前端框架** | React 18 + TypeScript | Vue 3, Svelte | 参考项目 EbookDatabase 使用 React，组件体系可复用 |
| **构建工具** | Vite | Webpack, CRA | 开发体验好，HMR 快，构建产物小 |
| **样式方案** | Tailwind CSS | Ant Design, MUI | EbookDatabase 使用 Tailwind，UI 风格统一 |
| **路由** | React Router v6 | TanStack Router | 轻量，满足 SPA 需求 |
| **状态管理** | Zustand | Redux, Jotai | 极简 API，适合中小规模状态 |
| **实时推送** | WebSocket | SSE, Polling | 双向通信，可扩展控制指令（暂停/取消） |
| **任务存储** | SQLite | Redis, PostgreSQL | 零依赖，单机部署，数据量小 |
| **打包工具** | PyInstaller | Nuitka, cx_Freeze | 成熟稳定，打包 FastAPI 兼容性好 |

### 2.3 关键设计决策

| 决策 | 理由 |
|------|------|
| **Python 后端（非 Go）** | 管道全部是 Python 代码（ebook-fuzzy-search, nlc_isbn, bookmarkget, pikepdf, ocrmypdf），用 Go 重写成本极高且无必要 |
| **线程池执行同步管道** | OCR（2-3 小时）和下载（10 分钟）是同步阻塞操作，必须丢到 `run_in_executor` 避免阻塞事件循环 |
| **WebSocket 推送进度** | 7 步管道每步耗时差异大（秒级到小时级），HTTP 轮询浪费资源，WebSocket 推送即时 |
| **OCR 强制单线程** | PaddlePaddle 多线程导致文字层静默乱码（非崩溃），`--jobs 1` 是唯一安全选择 |
| **Anna's Archive 走 subprocess(curl)** | execute_code 沙盒不走 http_proxy，用 subprocess 继承环境变量走代理 127.0.0.1:6244 |
| **EbookDatabase 请求绕过 WSL 代理** | localhost:10223 被 WSL 全局代理拦截，必须用 `urllib.request.ProxyHandler({})` 绕行 |
| **Z-File 用 Cookie 认证** | Token header 方式返回 41018，Cookie 会话方式可靠 |

---

## 三、开发阶段

```
Phase 1: 后端核心 ████████████████ (1-2 天)
Phase 2: 前端基础 ████████████████ (1-2 天)
Phase 3: 实时进度 ████████         (1 天)
Phase 4: 报告+配置  ████           (0.5 天)
Phase 5: 打包+部署  ████           (0.5 天)
                                     ─────────
                                     4-6 天
```

### Phase 1：后端核心 (1-2 天)

#### 任务 1.1：FastAPI 项目骨架

| 文件 | 内容 |
|------|------|
| `backend/main.py` | FastAPI 入口，CORS，静态文件挂载，lifespan |
| `backend/config.py` | 配置管理：加载/保存 `config.json`，读取 `auth.json` |
| `backend/requirements.txt` | 依赖声明 |

**验收标准**：`python main.py` 启动后访问 `/docs` 显示 Swagger UI，`/api/v1/health` 返回 `{"status":"ok"}`

#### 任务 1.2：检索 API

| 文件 | 内容 |
|------|------|
| `backend/api/search.py` | `/api/v1/search` 端点 |

**实现内容**：
- 三模式入口：书名 / ISBN / SS码
- EbookDatabase API 调用（`urllib.request.ProxyHandler({})` 绕 WSL 代理）
- NLC 元数据并行补全（ThreadPoolExecutor, max_workers=5）
- 书葵网书签获取（取首条候选，前 200 字预览截断）
- 分页返回
- 高级检索：`fields[]` + `queries[]` + `logics[]` + `fuzzies[]` 多条件

**验收标准**：`GET /api/v1/search?field=title&query=社会形态学&fuzzy=true` 返回符合 EbookDatabase JSON 格式的结果

#### 任务 1.3：任务 API + SQLite 存储

| 文件 | 内容 |
|------|------|
| `backend/task_store.py` | SQLite 任务持久化（CRUD） |
| `backend/api/tasks.py` | `/api/v1/tasks` REST 端点 |

**数据表**：
```sql
tasks (task_id, status, current_step, current_step_name,
       params, pipeline_state, steps, log_lines, report,
       created_at, updated_at, error)
```

**验收标准**：`POST /api/v1/tasks` → 返回 task_id；`GET /api/v1/tasks/{id}` → 返回任务详情

#### 任务 1.4：WebSocket 管理器

| 文件 | 内容 |
|------|------|
| `backend/ws_manager.py` | WebSocket 连接注册/频道订阅/广播/断开清理 |
| `backend/api/ws.py` | `/ws/tasks/{task_id}` WebSocket 路由 |

**推送消息类型**：
- `step_start` / `step_progress` / `step_complete` — 步骤状态
- `log` — 日志行追加
- `task_complete` / `task_error` — 任务终态
- `sync` — 新连接全量状态同步

**验收标准**：用浏览器 WebSocket 客户端连接，发送步骤事件后客户端收到对应 JSON 消息

#### 任务 1.5：管道执行器

| 文件 | 内容 |
|------|------|
| `backend/engine/pipeline.py` | 7 步管道编排 |
| `backend/scripts/parse_bookmark_hierarchy.py` | 书葵网书签层级推断（已从 skill 复制） |

**7 步执行流程**：
```
execute_pipeline(task_id, params)
  for each step:
    1. 更新 task_store 状态 → "running"
    2. 通过 WebSocket 广播 step_start
    3. run_in_executor(thread_pool, step_fn)
    4. 通过 WebSocket 广播 step_complete / step_progress / log
    5. 更新 task_store 步骤状态
    6. 如果失败 → broadcast task_error + return
  完成后:
    broadcast task_complete + 保存 report
```

**步骤依赖关系**：
```
Step 1 (检索) ─→ state.candidates[] ─→ Step 2 (下载) ─→ state.pdf_path
                                         ↓
         ┌───────────────────────────────┘
         ↓
Step 3 (OCR) ─→ state.ocr_pdf_path
         ↓
Step 3.5 (压缩) ─→ state.compressed_pdf_path
         ↓
Step 4 (书签) ─→ state.bookmarked_pdf_path
         ↓
Step 5 (上传) ─→ state.direct_link
         ↓
Step 6 (报告) ─→ state.report
```

**验收标准**：通过 API 触发完整管道，7 步全部执行，SQLite 和 WebSocket 均有正确记录

### Phase 2：前端基础 (1-2 天)

#### 任务 2.1：项目初始化

| 文件 | 内容 |
|------|------|
| `frontend/package.json` | 依赖声明 |
| `frontend/vite.config.ts` | Vite 配置（含 API 代理） |
| `frontend/tailwind.config.js` | Tailwind 配置 |
| `frontend/tsconfig.json` | TypeScript 配置 |
| `frontend/index.html` | 入口 HTML |
| `frontend/src/main.tsx` | React 入口 |
| `frontend/src/App.tsx` | 路由配置 |
| `frontend/src/types.ts` | TypeScript 类型定义 |

**验收标准**：`npm run dev` 启动，浏览器打开 http://localhost:3000 显示空白页面无报错

#### 任务 2.2：搜索页面（核心 UI）

| 文件 | 内容 |
|------|------|
| `frontend/src/pages/SearchPage.tsx` | 搜索主页面，三 Tab 切换 |
| `frontend/src/components/BasicSearchForm.tsx` | 基础检索表单 |
| `frontend/src/components/AdvancedSearchForm.tsx` | 高级检索表单（最多 6 条件） |
| `frontend/src/components/TaskListPanel.tsx` | 最近任务列表 |
| `frontend/src/components/Layout.tsx` | 全局导航栏 |
| `frontend/src/stores/useStore.ts` | Zustand 全局状态 |

**UI 设计规范（复刻 EbookDatabase）**：
```
┌─────────────────────────────────────────────┐
│         Book Downloader                      │
│     检索并下载电子书，全自动管道处理            │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ [基础检索] [高级检索] [最近任务]       │   │
│  │ ─────────────────────────────────── │   │
│  │                                      │   │
│  │  字段: [▼ 书名]                      │   │
│  │  关键词: [________________] [搜索]    │   │
│  │  ☑ 模糊搜索                          │   │
│  │                                      │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**验收标准**：
- 基础检索：选择字段 → 输入关键词 → 点击搜索 → 跳转结果页
- 高级检索：添加/删除条件 → 设置 AND/OR → 搜索
- 输入验证：ISBN 仅数字、不能提交空查询

#### 任务 2.3：搜索结果页

| 文件 | 内容 |
|------|------|
| `frontend/src/pages/ResultsPage.tsx` | 结果展示页 |
| `frontend/src/components/BookCard.tsx` | 单本书卡片组件 |

**每张卡片展示**：
- 书名（加粗）、作者 / 出版社
- ISBN / SS码 / 来源（DX_6.0 / DX_2.0-5.0）
- NLC 补全状态（绿色 ✓ 或灰色 —）
- 书葵网书签预览（折叠，前 200 字）
- **[开始下载]** 按钮 → 创建任务 → 跳转任务详情页

**验收标准**：搜索结果正确渲染卡片，点击"开始下载"成功创建任务并跳转

### Phase 3：实时进度 (1 天)

#### 任务 3.1：WebSocket 客户端

| 文件 | 内容 |
|------|------|
| `frontend/src/hooks/useTaskWebSocket.ts` | WebSocket 连接 + 状态管理 hook |

**功能**：
- 连接建立时接收 `sync` 全量状态
- 处理 6 种消息类型更新 UI
- 断线自动重连（任务未完成时，3 秒间隔）
- 任务完成后自动断开

**验收标准**：打开任务详情页 → WebSocket 连接建立 → 后端推送进度 → UI 实时更新

#### 任务 3.2：任务详情页

| 文件 | 内容 |
|------|------|
| `frontend/src/pages/TaskDetailPage.tsx` | 任务详情主页面 |
| `frontend/src/components/StepProgressBar.tsx` | 横向步骤进度条 |
| `frontend/src/components/LogStream.tsx` | 终端风格实时日志流 |

**页面布局**：
```
┌─────────────────────────────────────────────┐
│  任务详情  a1b2c3d4e5f6          ● 已连接    │
│                                              │
│  ┌─ 执行进度 ────────────────────────────┐  │
│  │                                        │  │
│  │  ✓检索 → ◌下载(45%) → ○OCR → ○压缩... │  │
│  │  [═══进度条══════]                      │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ 执行日志 ────────────────────────────┐  │
│  │ ██ [14:52:05] ■ 步骤 1/6: 检索信息     │  │
│  │ ██ [14:52:08] EbookDatabase 召回 3 条   │  │
│  │ ██ [14:52:12] NLC 补全完成              │  │
│  │ ██ [14:52:15] ■ 步骤 2/6: 下载 PDF     │  │
│  │ ██ [14:54:10] ✓ 下载完成 (45.2 MB)     │  │
│  │ ██                                      │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  (任务完成后显示)                             │
│  ┌─ 执行报告 ────────────────────────────┐  │
│  │  书名 / 作者 / ISBN / 直链 ...         │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**验收标准**：
- 步骤进度条正确反映 7 步状态
- 日志流逐行追加，自动滚动到底部
- OCR 步骤显示百分比进度
- 任务完成后展示报告（含下载链接）

### Phase 4：执行报告 + 配置 (0.5 天)

#### 任务 4.1：执行报告

| 文件 | 内容 |
|------|------|
| `backend/engine/pipeline.py` (step 6) | 报告生成逻辑 |
| `frontend/src/components/TaskReport.tsx` | 报告渲染组件 |

**报告内容**：
```
书名 / 作者 / 出版社 / ISBN
下载来源（Anna's Archive / Z-Library）
OCR 方案和耗时
书签状态（书葵网成功 / 仅目录页 / 无）

📎 直链（内网）：http://192.168.0.7:32771/directlink/1/xxx.pdf
📎 直链（外网）：https://zfile.vip.cpolar.top/directlink/1/xxx.pdf

最终文件大小: xx.x MB
```

**验收标准**：任务完成后报告正确渲染，直链可点击打开

#### 任务 4.2：配置管理

| 文件 | 内容 |
|------|------|
| `backend/config.py` | 已有配置管理 |
| `backend/api/search.py` | 新增 `/api/v1/config` GET/POST |

**前端配置界面**（集成到搜索页的配置 Tab 或独立弹窗）：
- EbookDatabase 地址
- stacks 地址
- Z-File 地址
- OCR 语言
- 代理设置

**验收标准**：通过 API 修改配置 → 配置文件更新 → 重启后生效

### Phase 5：打包与部署 (0.5 天)

#### 任务 5.1：PyInstaller 打包

| 文件 | 内容 |
|------|------|
| `backend/book-downloader.spec` | PyInstaller 配置 |
| `build_exe.py` | 一键构建脚本 |

**构建流程**：
```
1. npm run build (前端 → dist/)
2. pyinstaller book-downloader.spec
3. 输出 BookDownloader.exe
```

**验收标准**：`BookDownloader.exe` 双击启动 → 浏览器访问 `http://localhost:8000` → 显示搜索页面

#### 任务 5.2：systemd 部署

| 文件 | 内容 |
|------|------|
| `deploy/book-downloader-web.service` | systemd 服务文件 |

**关键配置**：
- `After=ebookdatabase.service docker.service`（依赖 EbookDatabase + stacks Docker）
- `Environment="TMPDIR=/home/eclaw/tmp/ocrmypdf"`（OCR 固定临时目录）
- `Restart=no`（长任务不宜自动重启）

**验收标准**：`systemctl start book-downloader-web` → 服务正常运行

---

## 四、目录结构

```
ebook-downloader/
├── backend/                          # Python FastAPI 后端
│   ├── main.py                       # 入口，FastAPI 应用创建
│   ├── config.py                     # 配置管理 (JSON)
│   ├── task_store.py                 # SQLite 任务 CRUD
│   ├── ws_manager.py                 # WebSocket 连接管理
│   ├── requirements.txt              # Python 依赖
│   ├── book-downloader.spec          # PyInstaller 打包
│   ├── api/
│   │   ├── __init__.py
│   │   ├── search.py                 # 检索 API
│   │   ├── tasks.py                  # 任务 API
│   │   └── ws.py                     # WebSocket 路由
│   ├── engine/
│   │   ├── __init__.py
│   │   └── pipeline.py              # 7 步管道编排 + 每步实现
│   └── scripts/
│       └── parse_bookmark_hierarchy.py  # 书签层级推断
├── frontend/                         # React + Vite + Tailwind 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx                  # React 入口
│       ├── App.tsx                   # 路由配置
│       ├── types.ts                  # TypeScript 类型
│       ├── index.css                 # Tailwind + 全局样式
│       ├── pages/
│       │   ├── SearchPage.tsx        # 搜索主页 (Tab: 基础/高级/任务)
│       │   ├── ResultsPage.tsx       # 搜索结果页
│       │   ├── TaskDetailPage.tsx    # 任务详情 (进度+日志+报告)
│       │   └── TaskListPage.tsx      # 历史任务列表
│       ├── components/
│       │   ├── Layout.tsx            # 全局导航栏
│       │   ├── BasicSearchForm.tsx   # 基础检索表单
│       │   ├── AdvancedSearchForm.tsx # 高级检索表单 (AND/OR 叠加)
│       │   ├── BookCard.tsx          # 搜索结果卡片
│       │   ├── StepProgressBar.tsx   # 步骤进度条
│       │   ├── LogStream.tsx         # 终端风格日志流
│       │   ├── TaskReport.tsx        # 执行报告
│       │   └── TaskListPanel.tsx     # 主页任务列表面板
│       ├── hooks/
│       │   └── useTaskWebSocket.ts   # WebSocket 客户端 hook
│       └── stores/
│           └── useStore.ts           # Zustand 状态管理
├── deploy/
│   └── book-downloader-web.service   # systemd 服务文件
├── config.default.json               # 默认配置模板
├── build_exe.py                      # 一键构建脚本
└── README.md                         # 项目文档
```

---

## 五、外部依赖

### 5.1 运行时服务依赖

| 服务 | 地址 | 用途 | 必需 |
|------|------|------|------|
| **EbookDatabase** | localhost:10223 | 图书元数据检索 | ✅ 检索 |
| **stacks Docker** | localhost:7788 | Anna's Archive 下载 | ✅ 下载 |
| **Z-File** | 192.168.0.7:32771 | 文件上传/直链 | ✅ 上传 |
| **ocrmypdf + PaddleOCR** | 系统命令行 | PDF OCR 识别 | ⚠️ OCR |
| **qpdf** | 系统命令行 | PDF 结构压缩 | ○ 压缩 |
| **nlc_isbn** | /home/eclaw/EbookDataGeter | NLC 元数据补全 | ⚠️ 检索 |
| **bookmarkget** | /home/eclaw/EbookDataGeter | 书葵网书签获取 | ⚠️ 检索 |
| **WSL2 代理** | 127.0.0.1:6244 | Anna's Archive 外网访问 | ✅ 下载 |

### 5.2 软件依赖版本

```
后端:  Python 3.11+, FastAPI 0.109+, uvicorn 0.27+
前端:  Node.js 18+, npm 9+, React 18.3+
构建:  PyInstaller 6.x (仅打包时需要)
PDF:   PyMuPDF 1.23+, pikepdf (书签注入)
OCR:   ocrmypdf 17+, paddleocr 3.2+, PaddlePaddle 3.0+
```

---

## 六、风险与对策

| 风险 | 影响 | 概率 | 对策 |
|------|------|------|------|
| **OCR 阻塞事件循环** | 服务无响应 | 高 | 丢到独立线程池 (`run_in_executor`)，设置超时 |
| **PaddlePaddle 多线程乱码** | OCR 文字层损坏 | 高 | 强制 `--jobs 1` + OCR 后用 `is_ocr_readable()` 检测 |
| **WSL2 /tmp 自动清理** | OCR 中途 FileNotFoundError | 中 | `TMPDIR=/home/eclaw/tmp/ocrmypdf` 固定目录 |
| **Anna's Archive 代理不生效** | 下载步骤超时 | 高 | 使用 `subprocess.run(curl)` 继承环境变量，不用 urllib |
| **Z-File Token 41018** | 上传失败 | 中 | Cookie 会话认证为主路径，Token 作备选 |
| **EbookDatabase 不可用** | 检索失败 | 中 | NLC fallback 构造候选，提供友好错误提示 |
| **stacks 下载队列积压** | 下载超时 | 中 | 指数退避轮询，最大 600 秒超时后降级到 Z-Library |
| **大文件 PyInstaller 打包** | .exe > 500MB | 中 | exclude numpy/matplotlib/tkinter，使用 upx 压缩 |
| **前端打包后路径错误** | 静态资源 404 | 低 | Vite `base: '/'`，FastAPI 挂载 `dist/` 目录 |
| **WSL2 全局代理拦截 localhost** | EbookDatabase 请求走代理失败 | 高 | `urllib.request.ProxyHandler({})` 绕过代理 |

---

## 七、测试策略

### 7.1 单元测试（后端）

```
backend/
├── tests/
│   ├── test_config.py        # 配置加载/保存
│   ├── test_task_store.py    # SQLite CRUD
│   ├── test_ws_manager.py    # WebSocket 广播/断开
│   ├── test_search.py        # 检索 API
│   ├── test_pipeline.py      # 管道步骤（mock 外部依赖）
│   └── test_bookmark.py      # 书签层级推断
```

### 7.2 集成测试（手动）

| 场景 | 步骤 |
|------|------|
| 书名检索 | 输入"社会形态学" → 期望召回多条候选 + NLC 补全 |
| ISBN 检索 | 输入"9787100193655" → 期望精确命中 |
| SS码检索 | 输入"12662374" → 期望精确命中 |
| 高级检索 | 书名="社会" AND 作者="哈布瓦赫" → 期望过滤结果 |
| 完整管道 | 搜索结果 → 开始下载 → 观察 7 步进度 → 获取报告和直链 |
| 配置修改 | 修改 EbookDatabase URL → 保存 → 检索生效 |
| 任务取消 | 管道执行中 → 取消 → 状态变为 cancelled |
| 断线重连 | 关闭浏览器标签 → 重新打开 → 状态恢复 |

### 7.3 前端测试

```bash
npm run build  # 确保 TypeScript 编译无错误
npm run lint   # ESLint 检查（待配置）
```

---

## 八、实施顺序

```
Day 1: Phase 1 后端核心
  ├─ 上午: FastAPI 骨架 + config.py + 检索 API
  └─ 下午: task_store + tasks API + ws_manager + WebSocket

Day 2: Phase 1 管道引擎
  ├─ 上午: 7 步管道编排 + 线程池执行
  └─ 下午: 联调后端所有 API → 可用 curl 验证完整流程

Day 3: Phase 2 前端基础
  ├─ 上午: Vite 项目初始化 + Layout + 类型定义
  └─ 下午: SearchPage + BasicSearchForm + AdvancedSearchForm

Day 4: Phase 2 前端页面 + Phase 3
  ├─ 上午: ResultsPage + BookCard + TaskListPage
  └─ 下午: TaskDetailPage + StepProgressBar + LogStream + useTaskWebSocket

Day 5: Phase 4 + Phase 5
  ├─ 上午: TaskReport + 配置管理前端界面
  └─ 下午: PyInstaller 打包 + systemd 服务 + 端到端测试

Day 6 (buffer): Bug 修复 + 文档完善
```

---

## 九、交付物清单

| 序号 | 交付物 | 格式 |
|------|--------|------|
| 1 | 完整源代码 | 42 个文件 |
| 2 | 后端 Python 包 | `backend/` 目录 |
| 3 | 前端 React 项目 | `frontend/` 目录 |
| 4 | Windows .exe | `build_exe.py` 构建产物 |
| 5 | systemd 服务配置 | `deploy/book-downloader-web.service` |
| 6 | API 文档 | FastAPI 自动生成 (`/docs`) |
| 7 | 默认配置模板 | `config.default.json` |
| 8 | 项目 README | `README.md` |
| 9 | 开发方案（本文档） | `DEVELOPMENT_PLAN.md` |
