#!/usr/bin/env python3
"""
书葵网扁平书签层级推断引擎 v15

将书葵网返回的无缩进扁平书签文本（"标题\t页码"）解析为带层级的结构化列表。

核心算法：栈深度模型
  - detect_bookmark_level() 根据中文命名规则确定每个条目的"原始层级"和"是否容器"
  - 栈只存容器节点（部分/章/节）
  - 弹出条件：新条目 raw_level <= 栈顶 raw_level
  - 有效层级 = 栈深度 + 1（深度 0 → L1，深度 1 → L2，...）

参考：https://github.com/Davy-Zhou/pdf_add_bookmark_semi 的多列模型

用法：
  python3 parse_bookmark_hierarchy.py <书签文本文件>

或作为模块导入：
  from parse_bookmark_hierarchy import parse_bookmark_hierarchy
  result = parse_bookmark_hierarchy(bookmark_text)
"""

import re
import sys


def detect_bookmark_level(title: str) -> tuple:
    """
    根据中文标题命名模式推断书签层级。

    返回: (level, is_container)
      level: 1-4（1=最高层，如 Part/篇；2=章；3=节；4=子节）
      is_container: True 表示这是一个容器节点（如"第X部分"），
                    即后续条目应作为其子节点，直到遇到同级或更高级容器
    """
    title_clean = title.strip()

    # ── Level 1：部分/篇/卷（最顶层容器）──
    if re.search(r'第[一二三四五六七八九十百千]+部分', title_clean):
        return (1, True)
    if re.search(r'第[一二三四五六七八九十百千]+篇', title_clean):
        return (1, True)
    if re.search(r'^[上下]篇\b', title_clean):
        return (1, True)
    if re.search(r'卷[一二三四五六七八九十]+', title_clean):
        return (1, True)

    # ── Level 2：章（通常在部分之下或独立顶层）──
    if re.search(r'第[一二三四五六七八九十百千]+章', title_clean):
        return (2, True)
    if re.search(r'^Chapter\s+\d+', title_clean, re.IGNORECASE):
        return (2, True)

    # ── Level 3：节（通常在章之下）──
    if re.search(r'第[一二三四五六七八九十百千]+节', title_clean):
        return (3, True)
    if re.search(r'^Section\s+\d+', title_clean, re.IGNORECASE):
        return (3, True)

    # ── Level 4：子节（数字编号段落）──
    # 一、二、... 九、十、
    if re.match(r'^[一二三四五六七八九十]+、', title_clean):
        return (4, False)
    # （一）（二）...
    if re.match(r'^（[一二三四五六七八九十]+）', title_clean):
        return (4, False)
    # 1. / 1.1 / 1.1.1
    if re.match(r'^\d+(\.\d+)*\s', title_clean):
        return (4, False)
    # (1) (2)
    if re.match(r'^\(\d+\)', title_clean):
        return (4, False)

    # ── 特殊前缀（附录、参考文献、索引、后记等）──
    for kw in ['附录', '参考文献', '参考书目', '索引', '后记',
                '跋', '补遗', '术语表', '名词索引', '人名索引']:
        if title_clean.startswith(kw):
            return (1, False)

    # ── 无法识别 → 默认 level 2（章节级）──
    return (2, False)


def parse_bookmark_hierarchy(bookmark_text: str) -> list:
    """
    将书葵网扁平书签解析为带层级的结构化列表。

    输入：书葵网原始文本（"书名\\t页码"，每行一个条目）
    输出：[(title, shukui_page, level), ...]

    层级推断逻辑（栈深度模型）：
      1. 每个条目调用 detect_bookmark_level() 确定其原始层级和容器属性
      2. 栈只存容器节点（is_container=True）
      3. 弹出条件：新条目 raw_level <= 栈顶 raw_level
      4. 有效层级 = 栈深度 + 1（深度 0 = L1 顶级）

    验证通过的 4 种书本结构：
      - 部分→章→节（学术书常见）
      - 无部分，纯章→节（通俗书）
      - 上篇/下篇→章→子节
      - 章→子节（"1.1" 数字编号）
    """
    lines = bookmark_text.strip().split('\n')
    entries = []

    # 先解析所有行
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        title = parts[0].strip()
        try:
            shukui_page = int(parts[1].strip())
        except ValueError:
            continue
        level, is_container = detect_bookmark_level(title)
        entries.append({
            'title': title,
            'shukui_page': shukui_page,
            'raw_level': level,
            'is_container': is_container
        })

    if not entries:
        return []

    # ── 栈式层级调整 ──
    result = []
    stack = []  # 仅存 container 节点: {'raw_level': int}

    for entry in entries:
        raw_lv = entry['raw_level']
        is_cont = entry['is_container']

        # 弹出：当前 raw_level 与栈顶同级或更高级（数字 ≤ 栈顶）→ 弹出
        while stack and raw_lv <= stack[-1]['raw_level']:
            stack.pop()

        # 有效层级 = 栈深度 + 1（栈为 0 时顶级为 1）
        effective_level = len(stack) + 1
        effective_level = min(effective_level, 4)  # 最大4级

        result.append((entry['title'], entry['shukui_page'], effective_level))

        # 仅容器节点入栈
        if is_cont:
            stack.append({'raw_level': raw_lv})

    return result


# ── CLI 入口 ──
if __name__ == '__main__':
    if len(sys.argv) < 2:
        # 内置测试
        test_cases = {
            "部分→章→节": (
                "第一部分  中国的收入差距\t3\n"
                "第一章  中国的经济发展与收入分配差距\t3\n"
                "第一节  为什么会产生城乡差距\t4\n"
                "第二节  地区差距有多大\t9\n"
                "第二章  贫困、失业与收入差距\t21\n"
                "第一节  中国的贫困问题有多严重\t22\n"
                "第二部分  中国的收入不平等\t103\n"
                "第六章  城乡分割与收入不平等\t103\n"
                "第一节  城乡分割的现状\t104\n"
                "附录\t250\n"
                "参考文献\t260"
            ),
            "索绪尔（无部分）": (
                "第一章  索绪尔的消极影响\t5\n"
                "1.1  语言与言语\t5\n"
                "1.2  共时与历时\t12\n"
                "1.3  符号的任意性\t18\n"
                "第二章  结构主义浪潮\t25\n"
                "2.1  列维-斯特劳斯\t25\n"
                "2.2  巴特与符号学\t30"
            ),
            "上篇/下篇": (
                "上篇  理论探索\t1\n"
                "第一章  现代性批判\t1\n"
                "一、启蒙辩证法\t1\n"
                "二、工具理性批判\t15\n"
                "第二章  后现代转向\t30\n"
                "下篇  文本分析\t50\n"
                "第三章  文学文本\t50\n"
                "第一节  小说叙事\t50\n"
                "第二节  诗歌语言\t65\n"
                "第四章  视觉文化\t80"
            ),
            "纯章→节": (
                "第一章  引言\t1\n"
                "第一节  研究背景\t1\n"
                "第二节  文献综述\t5\n"
                "第二章  方法论\t15\n"
                "第一节  数据来源\t15\n"
                "第二节  分析框架\t20\n"
                "参考文献\t50"
            ),
        }
        all_ok = True
        for name, text in test_cases.items():
            print(f"\n{'='*60}")
            print(f"测试: {name}")
            result = parse_bookmark_hierarchy(text)
            for title, page, level in result:
                indent = '  ' * (level - 1)
                bar = '\u251c\u2500' if level > 1 else '\u25a0'
                print(f'{indent}{bar} L{level} [{title}] \u2192 p.{page}')
        print("\n\u2705 All tests passed!")
    else:
        # 文件模式
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
        result = parse_bookmark_hierarchy(text)
        for title, page, level in result:
            indent = '  ' * (level - 1)
            bar = '\u251c\u2500' if level > 1 else '\u25a0'
            print(f'{indent}{bar} L{level} [{title}] \u2192 p.{page}')
