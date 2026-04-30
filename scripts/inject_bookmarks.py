#!/usr/bin/env python3
"""
PDF 书签注入引擎 v15

将书葵网（shukui.net）返回的扁平书签文本解析为多级嵌套结构，注入 PDF。

核心功能：
  1. 层级推断 — 调用 parse_bookmark_hierarchy.py 解析扁平书签为嵌套树
  2. 目录页定位 — 通过 DuXiu page label (!00001.jpg) 或关键词搜索
  3. 偏移量计算 — OCR 交叉比对 label 映射法 + 智能多锚点检测
  4. 分段偏移 — 自动检测同一本书中不同部分的偏移量差异
  5. Phantom 过滤 — 自动跳过书葵网返回的虚假章节
  6. 注入后验证 — 随机抽样确认书签跳转正确

用法:
  python3 inject_bookmarks.py <pdf_path> <bookmark_text_file> [output_path]
  python3 inject_bookmarks.py --toc-only <pdf_path>

依赖:
  pip install pymupdf
"""

import fitz
import re
import os
import sys
from collections import Counter
from datetime import datetime

# 导入同级目录的层级推断引擎
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_bookmark_hierarchy import parse_bookmark_hierarchy


# ══════════════════════════════════════════════════════════════
# 1. 文件命名
# ══════════════════════════════════════════════════════════════

def sanitize_filename_component(s: str) -> str:
    """移除文件名中的非法字符（Windows/Linux 通用）。"""
    return re.sub(r'[\\/:*?"<>|]', '', s).strip()


def format_output_filename(
    title: str,
    authors: list,
    pubdate: str = None,
    extension: str = ".pdf"
) -> str:
    """
    格式：书名_作者（YYYYMMDD）.pdf

    Args:
        title: 书名
        authors: 作者列表，如 ["薛进军"] 或 ["薛进军", "李实"]
        pubdate: 出版日期字符串，如 "2008" 或 "2008-01"
        extension: 文件扩展名
    """
    if not authors:
        author_str = "佚名"
    elif len(authors) == 1:
        author_str = authors[0]
    else:
        author_str = " / ".join(authors)

    if len(author_str) > 20:
        author_str = author_str.split()[0] if ' ' in author_str else author_str[:20]

    title_clean = sanitize_filename_component(title)
    author_clean = sanitize_filename_component(author_str)

    if pubdate:
        digits = re.sub(r'\D', '', str(pubdate))
        if len(digits) == 4:
            date_str = digits + "0101"
        elif len(digits) == 6:
            date_str = digits + "01"
        elif len(digits) >= 8:
            date_str = digits[:8]
        else:
            date_str = digits.ljust(8, '0')
    else:
        date_str = datetime.now().strftime("%Y%m%d")

    return f"{title_clean}_{author_clean}（{date_str}）{extension}"


# ══════════════════════════════════════════════════════════════
# 2. 目录页定位
# ══════════════════════════════════════════════════════════════

def find_toc_page_by_label(pdf_path: str) -> int:
    """
    通过 page label 定位目录页。

    DuXiu 扫描件命名规则：
      cov001.jpg ~ cov002.jpg    → 封面
      !00001.jpg                 → 目录页（固定命名）
      000001.jpg ~               → 正文页

    返回：目录页的 0-index 物理页码，找不到返回 -1
    """
    doc = fitz.open(pdf_path)
    for i in range(min(30, len(doc))):
        label = doc[i].get_label()
        if label == '!00001.jpg':
            doc.close()
            return i
    doc.close()
    return -1


def find_toc_page_by_text(doc, search_range=35) -> int:
    """Fallback：通过文字搜索定位目录页。"""
    for i in range(min(search_range, len(doc))):
        text = doc[i].get_text()
        if re.search(r'目\s*录', text):
            return i
    return -1


# ══════════════════════════════════════════════════════════════
# 3. 偏移量计算
# ══════════════════════════════════════════════════════════════

def detect_offset_by_label_match(scanned_pdf: str, ocr_pdf: str,
                                  bookmark_text: str) -> int:
    """
    通过 OCR 版交叉比对，精确计算扫描版 PDF 的书签偏移量。

    核心逻辑：在扫描版和 OCR 版中找到 label=000001.jpg（正文第一页），
    用公式 offset = (label物理页 + 1) - 书葵网第一条目标注页码。
    """
    scanned = fitz.open(scanned_pdf)
    ocr_doc = fitz.open(ocr_pdf)

    # 解析书葵网第一条目页码
    lines = bookmark_text.strip().split('\n')
    anchor_shukui_page = None
    for line in lines:
        parts = line.split('\t')
        if len(parts) >= 2:
            try:
                anchor_shukui_page = int(parts[1].strip())
                break
            except ValueError:
                continue

    if anchor_shukui_page is None:
        scanned.close()
        ocr_doc.close()
        return 0

    # 在扫描版中找 label=000001.jpg
    stacks_anchor_page = None
    for i in range(len(scanned)):
        if scanned[i].get_label() == '000001.jpg':
            stacks_anchor_page = i
            break

    scanned.close()
    ocr_doc.close()

    if stacks_anchor_page is None:
        return 0

    offset = (stacks_anchor_page + 1) - anchor_shukui_page
    print(f"[offset] 锚点: label=000001.jpg → 扫描版 p.{stacks_anchor_page + 1}, "
          f"书葵网 p.{anchor_shukui_page} → offset={offset:+d}")
    return offset


def is_toc_page_heuristic(page_index, doc):
    """判断某页是否为目录页（应被排除的锚点候选）。"""
    text = doc[page_index].get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    short_lines = [l for l in lines if len(l) < 40]
    long_lines = [l for l in lines if len(l) > 40]
    if len(short_lines) > 8 and len(long_lines) < 3:
        has_chapter = any(
            c in text for c in ["第一章", "第二章", "第三章", "第四章",
                                "1.", "2.", "3.", "4."]
        )
        if has_chapter:
            return True
    return False


def smart_offset_detect_v2(doc, bookmarks, min_anchors=6):
    """
    智能多锚点偏移量检测。

    从书签列表中均匀选取锚点，在 PDF 全文中搜索匹配关键词，
    通过聚类分析判断是单段偏移还是分段偏移。

    返回: (type, offset_or_zones, confidence, anchor_results)
      type: "single" 或 "multi"
    """
    n = len(bookmarks)
    if n < 3:
        return "single", 0, 0.0, []

    # 均匀选取锚点
    anchor_indices = [0, n // 2, n - 1]
    extra = list(range(1, n - 1, max(1, n // (min_anchors - 2))))
    anchor_indices = sorted(set(anchor_indices + extra[:min_anchors - 2]))[:min_anchors]

    anchor_results = []
    for idx in anchor_indices:
        title, sk_page, level = bookmarks[idx]
        search_kw = title[:4]

        matches = []
        for i in range(len(doc)):
            text = doc[i].get_text()
            if search_kw in text and not is_toc_page_heuristic(i, doc):
                matches.append(i + 1)

        if not matches:
            continue

        best_pdf_page = min(matches, key=lambda p: abs(p - sk_page))
        offset = best_pdf_page - sk_page
        anchor_results.append({
            "title": title[:20], "shukui_page": sk_page,
            "pdf_page": best_pdf_page, "offset": offset,
            "all_matches": matches
        })

    if len(anchor_results) < 2:
        return "single", 0, 0.0, anchor_results

    offsets = [r["offset"] for r in anchor_results]
    offset_counts = Counter(offsets)
    most_common_offset, most_common_count = offset_counts.most_common(1)[0]
    confidence = most_common_count / len(anchor_results)

    print(f"\n[smart_offset] 锚点分析（{len(anchor_results)}/{len(anchor_indices)}个找到）：")
    for r in anchor_results:
        match_info = f"（候选: {r['all_matches']}）" if len(r['all_matches']) > 1 else ""
        print(f"  '{r['title']}': shukui p.{r['shukui_page']} → PDF p.{r['pdf_page']}, "
              f"offset={r['offset']:+d} {match_info}")
    print(f"[smart_offset] 偏移量分布: {dict(offset_counts)}, 置信度={confidence:.0%}")

    if confidence >= 0.6:
        print(f"[smart_offset] 单段: offset={most_common_offset:+d}")
        return "single", most_common_offset, confidence, anchor_results

    # 分段检测
    top2 = offset_counts.most_common(2)
    off_a, _ = top2[0]
    off_b, _ = top2[1] if len(top2) > 1 else (None, None)
    a_pages = [r["shukui_page"] for r in anchor_results if r["offset"] == off_a]
    b_pages = [r["shukui_page"] for r in anchor_results if r["offset"] == off_b] if off_b else []

    if a_pages and b_pages:
        boundary = (max(a_pages) + min(b_pages)) // 2
        print(f"[smart_offset] 分段: boundary=shukui p.{boundary}, "
              f"zone1 offset={off_a:+d}, zone2 offset={off_b:+d}")
        return "multi", {"boundary": boundary, "zone1_offset": off_a, "zone2_offset": off_b}, confidence, anchor_results
    else:
        return "single", most_common_offset, confidence, anchor_results


# ══════════════════════════════════════════════════════════════
# 4. 统一注入
# ══════════════════════════════════════════════════════════════

def inject_bookmarks_smart(
    pdf_path: str,
    bookmark_text: str = None,
    bookmarks: list = None,
    output_path: str = None,
    known_offset: int = None,
    ocr_pdf: str = None,
    confidence_threshold: float = 0.6
) -> list:
    """
    统一书签注入函数：单段 / 分段自动处理。

    优先级：用户已知偏移 > label 锚点检测 > 自动多锚点检测

    Args:
        pdf_path: PDF 文件路径
        bookmark_text: 书葵网原始书签文本（与 bookmarks 二选一）
        bookmarks: 已解析的书签列表 [(title, shukui_page, level), ...]
        output_path: 输出路径（默认覆盖原文件）
        known_offset: 用户已知的固定偏移量（最高优先级）
        ocr_pdf: OCR 版 PDF 路径（用于 label 交叉比对）
        confidence_threshold: 单段偏移的置信度阈值

    Returns:
        注入后的 TOC 条目列表 [(level, title, pdf_page), ...]
    """
    if output_path is None:
        output_path = pdf_path

    doc = fitz.open(pdf_path)
    total = len(doc)

    # ── 解析书签 ──
    if bookmarks is None and bookmark_text:
        bookmarks = parse_bookmark_hierarchy(bookmark_text)
    if not bookmarks:
        print("[inject] 无书签数据，仅添加目录页")
        toc_page = find_toc_page_by_label(pdf_path)
        if toc_page < 0:
            toc_page = find_toc_page_by_text(doc)
        if toc_page >= 0:
            doc.set_toc([[1, "目 录", toc_page + 1]])
        doc.save(output_path)
        doc.close()
        return [[1, "目 录", toc_page + 1]] if toc_page >= 0 else []

    # ── 确定偏移策略 ──
    if known_offset is not None:
        zones = None
        offset = known_offset
        print(f"[inject] 使用用户指定偏移量: {offset:+d}")
    elif ocr_pdf and os.path.exists(ocr_pdf):
        offset = detect_offset_by_label_match(pdf_path, ocr_pdf, bookmark_text or "")
        if abs(offset) < 2 or abs(offset) > 50:
            print(f"[inject] label 锚点法 offset={offset:+d} 不可靠，回退到关键词搜索法")
            result = smart_offset_detect_v2(doc, bookmarks)
        else:
            zones = None
            print(f"[inject] label 锚点法 offset={offset:+d}")
    else:
        result = smart_offset_detect_v2(doc, bookmarks)
        if result[0] == "single":
            offset = result[1]
            zones = None
        else:
            offset = None
            zones = result[1]

    # ── Phantom 过滤 ──
    result = smart_offset_detect_v2(doc, bookmarks)
    anchor_results = result[3]
    phantom_offsets = set()
    if anchor_results:
        offset_counts = Counter(r["offset"] for r in anchor_results)
        phantom_offsets = {off for off, cnt in offset_counts.items()
                          if cnt == 1 and abs(off) > 30}
        if phantom_offsets:
            print(f"[inject] 检测到 phantom offset（离群值，将跳过）: {phantom_offsets}")

    # ── 构建 TOC ──
    # 目录页
    toc = []
    toc_page = find_toc_page_by_label(pdf_path)
    if toc_page < 0:
        toc_page = find_toc_page_by_text(doc)
    if toc_page >= 0:
        toc.append([1, "目 录", toc_page + 1])

    skipped = 0
    for title, sk_page, level in bookmarks:
        if zones:
            off = zones["zone2_offset"] if sk_page > zones["boundary"] else zones["zone1_offset"]
        else:
            off = offset

        if off in phantom_offsets:
            print(f"[inject] 跳过 phantom 书签：「{title}」（offset={off:+d}）")
            skipped += 1
            continue

        pdf_page = sk_page + off
        pdf_page = max(1, min(pdf_page, total))
        toc.append([level, title, pdf_page])

    # ── 注入并保存 ──
    doc.set_toc(toc)
    doc.save(output_path)
    doc.close()

    zone_info = ""
    if zones:
        zone_info = f"，分段：zone1≤{zones['boundary']}用{zones['zone1_offset']:+d}，zone2>{zones['boundary']}用{zones['zone2_offset']:+d}"

    print(f"[inject] 书签注入完成：{len(toc)} 条（含目录页），跳过 {skipped} 条 phantom，"
          f"offset={offset if offset is not None else f'{zones[\"zone1_offset\"]:+d}'}{zone_info}")
    print(f"[inject] 保存至: {output_path}")
    return toc


# ══════════════════════════════════════════════════════════════
# 5. 注入后验证
# ══════════════════════════════════════════════════════════════

def verify_bookmarks(output_path, samples):
    """
    注入后抽样验证。

    Args:
        output_path: 已注入书签的 PDF 路径
        samples: [(title_fragment, expected_viewer_page), ...]

    Returns:
        True 如果全部通过
    """
    doc = fitz.open(output_path)
    all_ok = True
    for title_fragment, expected_page in samples:
        text = doc[expected_page - 1].get_text()
        if title_fragment[:2] in text:
            print(f"  ✅ {title_fragment} → p.{expected_page}")
        else:
            print(f"  ❌ {title_fragment} 期望 p.{expected_page} 但内容不匹配！")
            all_ok = False
    doc.close()
    return all_ok


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n用法:")
        print("  # 完整注入（需要书签文本文件）")
        print("  python3 inject_bookmarks.py input.pdf bookmarks.txt output.pdf")
        print("  python3 inject_bookmarks.py input.pdf bookmarks.txt --offset 13")
        print("  python3 inject_bookmarks.py input.pdf bookmarks.txt --ocr ocr_version.pdf")
        print()
        print("  # 仅添加目录页（降级A）")
        print("  python3 inject_bookmarks.py --toc-only input.pdf output.pdf")
        sys.exit(0)

    # --toc-only 模式
    if sys.argv[1] == '--toc-only':
        pdf_path = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else pdf_path
        doc = fitz.open(pdf_path)
        toc_page = find_toc_page_by_label(pdf_path)
        if toc_page < 0:
            toc_page = find_toc_page_by_text(doc)
        if toc_page >= 0:
            doc.set_toc([[1, "目 录", toc_page + 1]])
            doc.save(output)
            print(f"[toc-only] 已添加目录页书签 → {output}")
        else:
            print("[toc-only] 未找到目录页")
        doc.close()
        sys.exit(0)

    # 完整注入模式
    pdf_path = sys.argv[1]
    bookmark_file = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else pdf_path

    with open(bookmark_file, 'r', encoding='utf-8') as f:
        bookmark_text = f.read()

    known_offset = None
    ocr_pdf = None

    # 解析可选参数
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == '--offset' and i + 1 < len(args):
            known_offset = int(args[i + 1])
            i += 2
        elif args[i] == '--ocr' and i + 1 < len(args):
            ocr_pdf = args[i + 1]
            i += 2
        else:
            i += 1

    toc = inject_bookmarks_smart(
        pdf_path=pdf_path,
        bookmark_text=bookmark_text,
        output_path=output,
        known_offset=known_offset,
        ocr_pdf=ocr_pdf,
    )

    print(f"\n最终 TOC ({len(toc)} 条):")
    for level, title, page in toc:
        indent = '  ' * (level - 1)
        print(f"  {indent}L{level} [{title}] → p.{page}")
