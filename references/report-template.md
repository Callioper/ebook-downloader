# 步骤 6：项目进度汇报模板

管道执行完成后，Agent 应按以下格式生成结构化报告，发送给用户。

---

## 格式约束

报告必须是纯文本（支持粗体、斜体），不使用代码框包裹，不使用 Markdown 表格。直链（下载链接）必须放在报告最前面，用户第一眼就要看到。

---

## 成功汇报模板

```
ebook-downloader 执行报告

ISBN: <isbn>
书名: <title>（<authors> / <publisher>）

📎 直链: <direct_link>
> 本地文件: <local_pdf_path>（仅供参考，实际交付以直链为准）

---

步骤1：检索信息 ✅
  ISBN: <isbn>
  SS码: <ss_code 或 "未查到">
  数据源: <EbookDatabase / NLC fallback>
  书签状态: <ok / not_found（书葵网未收录）>

步骤2：下载 PDF ✅
  来源: <stacks (Anna's Archive) / 其他>
  MD5: <md5>
  文件大小: <size> MB，<page_count> 页

步骤3：OCR ✅
  方案: <PaddleOCR / 跳过（已有文字层）>
  耗时: <duration>

步骤4：书签生成 ✅
  来源: <书葵网结构化书签 / 仅目录页（降级A）>
  书签条数: <N> 条（<M> 级嵌套）
  offset: <+N>

步骤5：上传 ✅
  直链: <direct_link>

---

📦 最终文件: <书名>_<作者>（<YYYYMMDD>）.pdf
```

---

## 部分失败汇报模板

```
ebook-downloader 执行报告（部分步骤失败）

ISBN: <isbn>
书名: <title>

---

步骤1：检索信息 ✅
  ...

步骤2：下载 PDF ✅
  ...

⚠️ 步骤3：OCR — 跳过
  原因: <PDF 已有文字层 / OCR 服务不可用>

❌ 步骤4：书签注入 — 失败
  原因: <pikepdf 权限错误 / 书签数据为空 / offset 无法确定>
  建议: <手动确认 offset 后重试>

步骤5：上传 ✅
  直链: <direct_link>
```

---

## 字段说明

| 字段 | 含义 | 取值示例 |
|------|------|---------|
| `isbn` | ISBN-13 | `9787544786672` |
| `ss_code` | 读秀 SS 码 | `12662374` 或 `未查到` |
| `数据源` | 元数据来源 | `EbookDatabase` / `NLC fallback` |
| `书签状态` | 书葵网书签获取结果 | `ok` / `not_found` |
| `来源`（下载） | 下载渠道 | `stacks (Anna's Archive)` / `Z-Lib` |
| `方案`（OCR） | OCR 引擎 | `PaddleOCR` / `跳过（已有文字层）` |
| `书签来源` | 书签数据来源 | `书葵网结构化书签` / `仅目录页（降级A）` |
| `offset` | 书签页码偏移量 | `+13` |
| `直链` | 文件分享链接 | URL |

---

## 安全注意事项

报告中不应包含以下信息：

- API Key 或 Token
- 内网 IP 地址（如 `192.168.x.x`）
- 服务登录凭证
- 本地文件系统的敏感路径（如 `/home/username/` 可用 `~/` 替代）

直链如有外网版本（通过隧道暴露），优先展示外网直链；如仅有内网直链，标注「内网访问」。
