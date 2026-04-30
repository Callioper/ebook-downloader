# Ghostscript pdfwrite 摧毁 OCR 文字层 — 实证报告

## 测试方法

使用一本 207 页的中文 OCR 版 PDF，分别用 Ghostscript pdfwrite 和 qpdf 处理后，逐页对比 CJK 字符数。

## 测试结果

### Ghostscript pdfwrite

```
页码 | OCR CJK | GS CJK | 保留率
p.1  |    21   |    0   |   0%
p.2  |    17   |    0   |   0%
p.3  |    21   |    0   |   0%
p.4  |   189   |    0   |   0%
p.5  |   597   |    0   |   0%
p.6  |   696   |    0   |   0%
p.7  |   464   |    0   |   0%
p.8  |   146   |    0   |   0%
p.9  |   451   |    0   |   0%
p.10 |   463   |    0   |   0%
p.11 |   511   |    0   |   0%
p.12 |   547   |    0   |   0%
p.13 |   566   |    0   |   0%
p.14 |   777   |    0   |   0%
p.15 |   515   |    0   |   0%
─────────────────────────────────────
15/15 页: 100% CJK 文字层丢失
```

**结论：Ghostscript pdfwrite 完全摧毁 OCR 文字层。** 即使 `-dPreserveAnnots=true` 也无法保护，因为 ocrmypdf 的透明文字层嵌入在页面内容流（content stream）中，不是 Annotations 对象。

### qpdf（结构压缩）

```
页码 | OCR CJK | qpdf CJK | 保留率
p.1  |    21   |    21    | 100%
p.5  |   597   |   597    | 100%
p.10 |   463   |   463    | 100%
p.15 |   515   |   515    | 100%
─────────────────────────────────────
全部页面: 100% CJK 文字层保留
```

**结论：qpdf 完全保留文字层。** qpdf 只做 PDF 结构层面的压缩（对象流重组、Flate 流重编码），不解释或修改页面内容流。

## 测试命令

```bash
# Ghostscript 压缩
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.7 \
   -dColorConversionStrategy=/Gray -dProcessColorModel=/DeviceGray \
   -dDownsampleMonoImages=false \
   -dAutoFilterMonoImages=false -dMonoImageFilter=/CCITTFaxEncode \
   -dDownsampleGrayImages=false \
   -dAutoFilterGrayImages=false -dGrayImageFilter=/FlateEncode \
   -dDownsampleColorImages=false \
   -dAutoFilterColorImages=false -dColorImageFilter=/FlateEncode \
   -dPreserveAnnots=true -dHaveTransparency=false \
   -dNOPAUSE -dBATCH -dQUIET \
   -sOutputFile=output_gs.pdf input_ocr.pdf

# qpdf 结构压缩
qpdf --recompress-flate --object-streams=generate \
  input_ocr.pdf output_qpdf.pdf

# CJK 对比
python3 -c "
import fitz
for path in ['input_ocr.pdf', 'output_gs.pdf', 'output_qpdf.pdf']:
    doc = fitz.open(path)
    cjk = sum(1 for i in range(min(15, len(doc)))
              for c in doc[i].get_text() if '\u4e00' <= c <= '\u9fff')
    print(f'{path}: {cjk} CJK chars in first 15 pages')
    doc.close()
"
```

## 根因分析

Ghostscript pdfwrite 是一个完整的 PDF 重解释器（re-interpreter），不是编码器或压缩器。它的工作方式决定了 OCR 文字层必然被摧毁：

1. 重新光栅化所有页面
2. 重新构建页面内容流（content streams）
3. 重新编码字体和文本
4. ocrmypdf 的透明文字层（render_mode=3 的不可见文本）嵌入在内容流中
5. pdfwrite 重建内容流时，不可见文本被丢弃
6. `-dPreserveAnnots=true` 只保护 PDF Annotation 对象（如链接、注释），不保护内容流

## 正确做法

OCR 后的 PDF 如需压缩，只能用以下两种安全方法：

- `ocrmypdf --optimize 1 input.pdf output.pdf` — ocrmypdf 内置优化，识别并保护自身生成的文字层
- `qpdf --recompress-flate --object-streams=generate input.pdf output.pdf` — 纯结构压缩，完全不触碰页面内容流

绝对不要对 OCR 后的 PDF 使用 Ghostscript 的 `pdfwrite` 设备。
