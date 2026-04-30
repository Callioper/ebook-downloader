# 下载错误分类与排查

## 错误类型

下载过程中的错误分为两类，处理方式不同。

**临时错误（transient）：** 重试可恢复。包括网络超时、连接拒绝、镜像暂时不可用、速率限制（Too many requests）。处理方式：指数退避重试，最多 3 次，间隔递增（5s / 10s / 20s）。

**永久错误（permanent）：** 重试无效。包括文件不存在（No mirrors found / File not found）、MD5 无效（Invalid MD5）、访问拒绝（Access denied）、哈希不匹配（Hash mismatch）。处理方式：立即终止当前 MD5 的下载尝试，切换到下一个候选 MD5 或其他下载源。

## 常见失败场景

### stacks 返回 "Already downloaded successfully"

原因：之前会话已经下载过这个 MD5，文件在磁盘上但会话中断后路径记录不清晰。

排查：检查 stacks 的下载目录。如果使用 docker-compose，路径可能在 `~/stacks/stacks/download/`（嵌套 compose 解析）或 `~/stacks/download/`（直接 compose 解析）。两个路径都检查。

### stacks 返回 "Invalid MD5"

原因：误将 EbookDatabase 的 `second_pass_code`（DuXiu 复合字段，格式为 `MD5_part1#MD5_part2#filesize#filename`）当作 Anna's Archive 的 32 位十六进制 MD5 使用。

解决：必须用书名或 ISBN 从 Anna's Archive 搜索页获取真实 MD5。命令：`curl "https://annas-archive.gd/search?q={书名}" | grep -oP '/md5/[a-f0-9]{32}'`

### stacks 返回 "No mirrors found"

原因：该书不在 Anna's Archive 的数据库中。这是永久错误，当前 MD5 不可用。

解决：切换到候选列表中的下一个 MD5（不同版本/格式）。如果所有 MD5 都不可用，降级到 Z-Library 或 LibGen。

### stacks 连接拒绝

原因：stacks 服务未启动。

排查：`docker ps | grep stacks` 确认容器状态。如果没在运行，`cd ~/stacks && docker compose up -d` 启动。如果根本没有部署，参考 SKILL.md 步骤② 的 docker-compose 快速启动。

### stacks 文件不在预期路径

原因：docker-compose 的 `./stacks/download` 卷映射在 compose 上下文中解析为嵌套路径 `~/stacks/stacks/download/`，而不是 `~/stacks/download/`。

解决：同时检查两个路径。如果文件仍找不到，用 `docker cp stacks:/opt/stacks/download/{filename} ~/stacks/download/` 从容器中提取。

### Anna's Archive 搜索无结果

原因：书名含特殊字符或中文编码问题。或者该书确实不在 Anna's Archive 中。

解决：换用 ISBN 搜索（更精确）。或通过 SS 码搜索（Anna's Archive 接受读秀 SS 码作为查询词）。去掉书名中的标点符号（如「·」「——」）重试。

### Anna's Archive 搜索超时

原因：Anna's Archive 域名在部分地区被封锁，或代理未配置/已失效。

排查：先确认代理可用：`curl -x http://127.0.0.1:7890 https://annas-archive.gd`。如果代理正常但仍超时，可能是 Anna's Archive 正在维护，等待 1-2 小时后重试。

## 下载后文件类型修正

stacks 下载的文件可能名不符实，需要检测实际内容：

- 文件扩展名是 `.zip`，但文件头是 `%PDF-1.4` → 纯 PDF 被错误命名，直接重命名为 `.pdf`
- 文件扩展名是 `.zip`，内容是 ZIP 包含 PDG/JPG 图片序列 → 使用 Pillow + PyMuPDF 逐页合成为 PDF
- 文件扩展名是 `.pdf`，但实际是 HTML 错误页（文件大小 < 10KB）→ 下载失败，丢弃文件

用 `file downloaded_file` 和 `head -c 100 downloaded_file | xxd` 快速确认文件真实类型。
