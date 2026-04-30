# 评测用例与最小可跑路径

本文件提供端到端验证用例，确保管道各步骤在**没有自建基础设施**的情况下也能跑通核心路径。

---

## 最小可跑路径（零基础设施起步）

如果你没有任何本地服务（无 EbookDatabase、无 stacks、无 Z-File），按以下步骤验证管道的核心下载和 OCR 功能：

### 前置：安装 OCR 工具

```bash
pip install ocrmypdf ocrmypdf-paddleocr paddlepaddle paddleocr
```

### 路径：纯 Anna's Archive 搜索 → curl 下载 → OCR

此路径只依赖公网（需代理访问 Anna's Archive），不需要任何本地服务。

**步骤1：搜索并确认 MD5**

```bash
# 用一本确定存在的书测试（示例：《社会形态学》，中文社会学经典）
curl -s --max-time 20 \
  "https://annas-archive.gd/search?q=社会形态学" \
  | grep -oP '/md5/[a-f0-9]{32}' | head -3
```

期望输出：至少 1 个 `/md5/` 链接。

**步骤2：选择第一个 MD5，获取下载页信息**

```bash
MD5="从步骤1获取的MD5"
curl -s --max-time 20 \
  "https://annas-archive.gd/md5/$MD5" \
  | grep -oP 'filesize[^>]*>[0-9,]+' | head -1
```

期望输出：类似 `filesize_bytes:9268116` 的文件大小信息。

**步骤3：通过下载管理器（stacks）下载**

如果已部署 stacks：
```bash
curl -X POST "http://localhost:7788/api/queue/add" \
  -H "X-API-Key: $DOWNLOAD_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"md5\": \"$MD5\"}"
```
然后轮询 `GET /api/status` 直到下载完成。

如果没有 stacks，尝试直接从 Anna's Archive 下载页获取直链：
```bash
curl -s --max-time 30 \
  "https://annas-archive.gd/md5/$MD5" \
  | grep -oP 'href="[^"]*\.(pdf|epub)[^"]*"' | head -1
```

**步骤4：OCR（验证核心功能）**

```bash
# 强制 --jobs 1（防乱码）
ocrmypdf --plugin ocrmypdf_paddleocr -l chi_sim+eng \
  --jobs 1 --output-type pdf --mode force \
  downloaded.pdf downloaded_ocr.pdf

# 验证文字层
python3 -c "
import fitz
doc = fitz.open('downloaded_ocr.pdf')
text = doc[5].get_text()  # 第6页
cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
print(f'第6页 CJK 字符数: {cjk}')
print(f'文字层有效: {cjk > 50}')
"
```

期望：第6页 CJK ≥ 50 → OCR 成功。

---

## 评测用例（7个场景）

以下用例覆盖管道中的关键决策分支。标注 ✅ 的为已验证的原版路径。

### 用例1：书名模式（✅ 原版验证）

**输入：** `形而上学的巴别塔`
**触发：** 用户说「下载 《形而上学的巴别塔》」
**期望行为：**
1. 步骤①：EbookDatabase 模糊搜索命中多个候选 → NLC 校验 → 书葵网书签
2. 步骤②：用 SS 码或书名从 Anna's Archive 搜索 MD5 → stacks 下载
3. 步骤③：OCR → `is_ocr_readable()` 检测通过
4. 步骤④：书葵网书签注入（三层降级：正常注入）
5. 步骤⑤：上传 Z-File → 生成直链
6. 步骤⑥：结构化报告，列出所有步骤结果

### 用例2：ISBN 模式（✅ 原版验证）

**输入：** `9787544786672`
**触发：** 用户输入 ISBN
**期望行为：**
1. 步骤①：EbookDatabase ISBN 精确查询 → 未命中 → NLC fallback 构造候选（`_fallback: true`）
2. 步骤②：直接以 ISBN 搜索 Anna's Archive → 提取 MD5 → 下载
3. 步骤④：`_fallback` 候选的书签来自 NLC fallback 同步获取的书葵网书签

### 用例3：SS 码模式（✅ 原版验证）

**输入：** `12662374`
**触发：** 用户提供 SS 码
**期望行为：**
1. 步骤①：EbookDatabase SS 码精确查询 → 命中
2. 步骤②：优先用 SS 码搜索 Anna's Archive，同时用候选的 ISBN 搜索

### 用例4：书签降级A（无书葵网书签）

**输入：** 一本在 EbookDatabase 有记录但书葵网无书签的书
**期望行为：**
1. 步骤①：EbookDatabase 命中 → 书葵网返回 `bookmark: null`
2. 步骤④：自动走降级A → 仅添加目录页书签
3. 步骤⑥：报告中标注「书签来源：仅目录页」

### 用例5：跳过 OCR（PDF 已有文字层）

**输入：** 一本 PDF 本身含文字层（非扫描件）
**期望行为：**
1. 步骤③：检测 PDF 已有文字层 → 跳过 OCR → 直接进入步骤④
2. 不影响后续步骤

### 用例6：零基础设施路径（本次新增）

**输入：** 任意已知存在于 Anna's Archive 的书名
**前置：** 无 EbookDatabase、无 stacks、无书葵网
**期望行为：**
1. 步骤①：纯 Anna's Archive 搜索 → 书名解析为 MD5 列表
2. 步骤②：如果有 stacks，用 stacks 下载；否则尝试 curl 直链
3. 步骤③：OCR（正常执行）
4. 步骤④：降级A（无书葵网 → 仅目录页）
5. 输出：本地可搜索 PDF

**验证通过标准：** 至少生成一个可搜索的 PDF，OCR 后第 3-5 页 CJK 比率 ≥ 1%。

### 用例7：OCR 乱码防御验证

**输入：** 任意扫描件 PDF
**验证步骤：**
```bash
# 故意用 --jobs 4（触发已知 bug）
ocrmypdf --plugin ocrmypdf_paddleocr -l chi_sim+eng \
  --jobs 4 --output-type pdf --mode force \
  input.pdf output_broken.pdf

# 检测乱码
python3 -c "
import fitz
doc = fitz.open('output_broken.pdf')
text = doc[10].get_text()
cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
print(f'CJK: {cjk} → {\"乱码\" if cjk < 10 else \"正常\"}'  )"
```
**期望结果：** `--jobs 4` 产生乱码（CJK < 10），验证了 `--jobs 1` 的必要性。

---

## 管道完整性自检清单

跑完最小可跑路径后，逐项确认：

- [ ] Anna's Archive 搜索能返回 MD5（步骤①核心公网依赖可用）
- [ ] OCR 输出 PDF 文字层 CJK 比率 ≥ 1%（OCR 管道正常）
- [ ] 如果部署了 EbookDatabase，`curl localhost:10223/api/v1/search?query=测试&field=title` 返回 JSON
- [ ] 如果部署了 stacks，`curl localhost:7788/api/status` 返回状态 JSON
- [ ] `python3 scripts/parse_bookmark_hierarchy.py` 无参数运行 → 输出 4 组测试用例的解析结果

全部通过 → 管道基础就绪，可以处理真实图书下载请求。
