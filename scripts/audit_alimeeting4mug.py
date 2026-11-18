#!/usr/bin/env python3
"""只读审计 AliMeeting4MUG 双层 ZIP，并生成 Markdown 报告。

运行：python3 scripts/audit_alimeeting4mug.py
只依赖 Python 标准库；不会解压到 data/raw，也不会修改压缩包。
"""

import argparse
import collections
import csv
import difflib
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = PROJECT / "data/raw/cccdbe6d-87c3-4314-908e-f735073412a9.zip"
DEFAULT_REPORT = PROJECT / "outputs/audits/data_audit.md"
DEFAULT_INVENTORY = PROJECT / "outputs/audits/meeting_inventory.csv"
SPLIT_NAMES = {
    "train.zip": "Train",
    "dev.zip": "Dev",
    "except_TS_test1.zip": "Test1（except_TS_test1）",
}

# 这些样本编号是检查过的 Train 原文；脚本会核对它们仍在训练划分。
# 第五例刻意展示空标签会议中值得人工复核的语句，不能推断整场都无行动。
EXAMPLES = [
    ("M4017", 680, 3, "明确要求一周内完成两个方案；原句有时间要求，负责人仍需结合上下文确认。"),
    ("M0091", 658, 2, "说话人表示现在去查，原始标签命中这一句；上下文包含别人的查询请求。"),
    ("M3244", 34, 2, "说话人承诺后续筛选学生，动作有方向但没有具体截止日期。"),
    ("M1989", 1, 2, "原始标签命中‘今年我们公司举办运动会’，单句更像背景陈述；需要人工核对行动项定义及上下文。"),
    ("M0099", 4, 2, "整场 action_ids 为空，但这句含‘先调查一下’；需人工判断标注定义或漏标风险。"),
]


def sha256_file(path):
    """分块计算原始压缩包指纹，避免为了求哈希一次读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def percentile(values, percent):
    """按升序列表计算线性插值分位数；无数据返回 None。"""
    if not values:
        return None
    pos = (len(values) - 1) * percent / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return "无可用数据"
    parts = [("最小", ordered[0]), ("P10", percentile(ordered, 10)),
             ("P25", percentile(ordered, 25)), ("中位", percentile(ordered, 50)),
             ("P75", percentile(ordered, 75)), ("P90", percentile(ordered, 90)),
             ("P95", percentile(ordered, 95)), ("P99", percentile(ordered, 99)),
             ("最大", ordered[-1])]
    return "；".join("{} {}".format(k, round(v, 2) if isinstance(v, float) and not v.is_integer() else int(v)) for k, v in parts)


def normalize_text(text):
    """仅用于检测跨划分近似副本：合并空白，不改变审计输入。"""
    return re.sub(r"\s+", "", text)


def format_number(n):
    return f"{n:,}"


def format_pct(n, d):
    return "—" if not d else "{:.3f}%".format(n / d * 100)


def new_split_stats():
    return {
        "rows": 0, "parsed": 0, "parse_fail": collections.Counter(),
        "missing_label": 0, "null_label": 0, "invalid_label": 0,
        "empty_label": 0, "positive_meetings": 0,
        "usable_label_meetings": 0, "raw_action_ids": 0,
        "unique_action_ids": 0, "matched_action_ids": 0,
        "unmatched_action_ids": 0, "duplicate_action_ids": 0,
        "duplicate_sentence_ids": 0, "duplicate_meeting_ids": 0,
        "sentences": 0, "labeled_sentences": 0,
        "meeting_lengths": [], "sentence_lengths": [],
        "action_per_meeting": [], "invalid_sentence_rows": 0,
        "invalid_sentence_items": 0, "invalid_action_items": 0,
        "meeting_keys": collections.Counter(), "candidate_counts": collections.Counter(),
        "topic_candidate_counts": collections.Counter(),
        "sentence_item_shapes": collections.Counter(),
        "action_item_shapes": collections.Counter(),
        "sentence_id_types": collections.Counter(),
        "action_id_types": collections.Counter(),
        "examples_of_errors": [],
    }


def detect_table_delimiter(inner, member):
    """只看实际表头识别分隔符；正文含大量 JSON 逗号，不用全文件 Sniffer 猜测。"""
    with inner.open(member) as binary:
        header = binary.readline().decode("utf-8-sig").rstrip("\r\n")
    for delimiter in ("\t", ",", ";"):
        if next(csv.reader([header], delimiter=delimiter)) == ["idx", "content"]:
            return delimiter
    raise ValueError(f"无法识别 {member.filename} 的 idx/content 表头：{header!r}")


def add_error(stats, kind, location):
    stats["parse_fail"][kind] += 1
    if len(stats["examples_of_errors"]) < 12:
        stats["examples_of_errors"].append((kind, location))


def canonical_id(value):
    """只比较同一 ID 的整数/数字字符串表示；无法确定的类型原样标记。"""
    if isinstance(value, bool):
        return "bool:" + repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return str(int(value))
    return type(value).__name__ + ":" + repr(value)


def audit_record(record, stats, split, row_number, identities, train_examples, inventory,
                 long_sentence_fingerprints, transcripts):
    """检查一场会议的结构、标签和 ID；缺失标签保持缺失。"""
    if not isinstance(record, dict):
        add_error(stats, "content_not_object", f"{split} 行 {row_number}")
        return
    key = record.get("meeting_key")
    if not isinstance(key, str) or not key:
        add_error(stats, "missing_or_invalid_meeting_key", f"{split} 行 {row_number}")
        return
    sentences = record.get("sentences")
    if not isinstance(sentences, list):
        stats["invalid_sentence_rows"] += 1
        add_error(stats, "missing_or_invalid_sentences", f"{split} {key}")
        return

    stats["parsed"] += 1
    stats["meeting_keys"][key] += 1
    if stats["meeting_keys"][key] > 1:
        stats["duplicate_meeting_ids"] += 1
    stats["meeting_lengths"].append(len(sentences))
    stats["sentences"] += len(sentences)

    sentence_ids = collections.Counter()
    sentence_texts = []
    for sent in sentences:
        if not isinstance(sent, dict):
            stats["invalid_sentence_items"] += 1
            sentence_texts.append("")
            continue
        stats["sentence_item_shapes"][tuple(sorted(sent))] += 1
        sid = sent.get("id")
        stats["sentence_id_types"][type(sid).__name__] += 1
        if sid is not None:
            sentence_ids[canonical_id(sid)] += 1
        else:
            stats["invalid_sentence_items"] += 1
        text = sent.get("s")
        if not isinstance(text, str):
            stats["invalid_sentence_items"] += 1
            text = ""
        stats["sentence_lengths"].append(len(text))
        sentence_texts.append(text)
        if len(normalize_text(text)) >= 30:
            fingerprint = sha256_bytes(normalize_text(text).encode("utf-8"))
            long_sentence_fingerprints[fingerprint].add((split, key, canonical_id(sid)))
    stats["duplicate_sentence_ids"] += sum(n - 1 for n in sentence_ids.values() if n > 1)
    this_sentence_lengths = [len(s) for s in sentence_texts]

    # 检测同一会议 ID 和相同全文跨划分出现；不把句子编号跨会议重复视为错误。
    transcript = "\n".join(sentence_texts)
    transcripts[(split, key)] = " ".join(normalize_text(text) for text in sentence_texts)
    exact_hash = sha256_bytes(transcript.encode("utf-8"))
    normalized_hash = sha256_bytes(normalize_text(transcript).encode("utf-8"))
    identities.append((split, key, exact_hash, normalized_hash, row_number))

    inventory_row = {
        "split": split, "meeting_key": key, "csv_row": row_number,
        "sentence_count": len(sentences),
        "sentence_chars_min": min(this_sentence_lengths) if this_sentence_lengths else "",
        "sentence_chars_median": percentile(sorted(this_sentence_lengths), 50),
        "sentence_chars_p90": round(percentile(sorted(this_sentence_lengths), 90), 2) if this_sentence_lengths else "",
        "sentence_chars_max": max(this_sentence_lengths) if this_sentence_lengths else "",
        "action_label_status": "", "action_id_count": "", "action_id_unmatched": "",
        "sentence_id_duplicate_count": sum(n - 1 for n in sentence_ids.values() if n > 1),
        "transcript_sha256": exact_hash,
    }
    inventory.append(inventory_row)

    candidates = record.get("candidate")
    stats["candidate_counts"][len(candidates) if isinstance(candidates, list) else "非列表/缺失"] += 1
    topics = record.get("topic_segment_ids")
    if isinstance(topics, list):
        for topic in topics:
            if isinstance(topic, dict):
                votes = topic.get("candidate")
                stats["topic_candidate_counts"][len(votes) if isinstance(votes, list) else "非列表/缺失"] += 1

    if "action_ids" not in record:
        stats["missing_label"] += 1
        inventory_row["action_label_status"] = "missing"
        return
    actions = record["action_ids"]
    if actions is None:
        stats["null_label"] += 1
        inventory_row["action_label_status"] = "null"
        return
    if not isinstance(actions, list):
        stats["invalid_label"] += 1
        inventory_row["action_label_status"] = "invalid"
        return
    if not actions:
        stats["empty_label"] += 1
    valid_actions = []
    for action in actions:
        if not isinstance(action, dict) or "id" not in action or action["id"] is None:
            stats["invalid_action_items"] += 1
            continue
        stats["action_item_shapes"][tuple(sorted(action))] += 1
        stats["action_id_types"][type(action["id"]).__name__] += 1
        valid_actions.append(canonical_id(action["id"]))
    if len(valid_actions) != len(actions):
        stats["invalid_label"] += 1
        inventory_row["action_label_status"] = "invalid"
        return
    stats["usable_label_meetings"] += 1
    if valid_actions:
        stats["positive_meetings"] += 1
    stats["labeled_sentences"] += len(sentences)
    stats["raw_action_ids"] += len(valid_actions)
    stats["action_per_meeting"].append(len(valid_actions))
    unique_actions = set(valid_actions)
    stats["unique_action_ids"] += len(unique_actions)
    stats["duplicate_action_ids"] += len(valid_actions) - len(unique_actions)
    stats["matched_action_ids"] += sum(a in sentence_ids for a in unique_actions)
    stats["unmatched_action_ids"] += sum(a not in sentence_ids for a in unique_actions)
    inventory_row["action_label_status"] = "empty" if not actions else "positive"
    inventory_row["action_id_count"] = len(unique_actions)
    inventory_row["action_id_unmatched"] = sum(a not in sentence_ids for a in unique_actions)

    if split == "Train" and key in {example[0] for example in EXAMPLES}:
        train_examples[key] = {"sentences": sentences, "actions": unique_actions}


def inspect_archive(archive):
    """逐层按文件签名识别 ZIP，再用制表符 CSV + JSON 读取，不向磁盘解压。"""
    if not zipfile.is_zipfile(archive):
        raise ValueError("输入文件不是有效 ZIP")
    structure = []
    stats = {label: new_split_stats() for label in SPLIT_NAMES.values()}
    identities = []
    train_examples = {}
    inventory = []
    long_sentence_fingerprints = collections.defaultdict(set)
    transcripts = {}
    csv.field_size_limit(100_000_000)
    with zipfile.ZipFile(archive) as outer:
        bad = outer.testzip()
        if bad:
            raise ValueError("外层 ZIP CRC 校验失败：" + bad)
        names = [i.filename for i in outer.infolist() if not i.is_dir()]
        unexpected = sorted(set(names) - set(SPLIT_NAMES))
        missing = sorted(set(SPLIT_NAMES) - set(names))
        if unexpected or missing:
            raise ValueError(f"外层文件不符合已检查的格式：意外={unexpected} 缺少={missing}")
        for info in outer.infolist():
            if info.is_dir():
                structure.append((info.filename, info.file_size, info.compress_size, "directory"))
                continue
            data = outer.read(info)
            if not zipfile.is_zipfile(io.BytesIO(data)):
                raise ValueError(f"{info.filename} 的内容不是嵌套 ZIP")
            structure.append((info.filename, info.file_size, info.compress_size, sha256_bytes(data)))
            split = SPLIT_NAMES[info.filename]
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                bad = inner.testzip()
                if bad:
                    raise ValueError(f"{info.filename} 内层 ZIP CRC 校验失败：{bad}")
                files = [i for i in inner.infolist() if not i.is_dir()]
                if len(files) != 1:
                    raise ValueError(f"{info.filename} 应只有一个数据文件，实际 {len(files)} 个")
                member = files[0]
                delimiter = detect_table_delimiter(inner, member)
                delimiter_name = {"\t": "Tab", ",": "comma", ";": "semicolon"}[delimiter]
                structure.append((f"{info.filename}/{member.filename}", member.file_size,
                                  member.compress_size, f"UTF-8 {delimiter_name}-separated CSV, content=JSON"))
                with inner.open(member) as binary:
                    text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                    reader = csv.DictReader(text, delimiter=delimiter)
                    if reader.fieldnames != ["idx", "content"]:
                        raise ValueError(f"{member.filename} 列名不是已探测的 idx/content: {reader.fieldnames}")
                    for row_number, row in enumerate(reader, start=2):
                        group = stats[split]
                        group["rows"] += 1
                        if None in row or not isinstance(row.get("content"), str):
                            add_error(group, "invalid_tsv_row", f"{split} 行 {row_number}")
                            continue
                        try:
                            record = json.loads(row["content"])
                        except json.JSONDecodeError:
                            add_error(group, "invalid_json_content", f"{split} 行 {row_number}")
                            continue
                        audit_record(record, group, split, row_number, identities, train_examples,
                                     inventory, long_sentence_fingerprints, transcripts)
    return (structure, stats, identities, train_examples, inventory,
            long_sentence_fingerprints, transcripts)


def cross_split_overlaps(identities):
    """分别检查会议键、全文及空白归一化全文；这是精确重复检查，不是语义近重复检测。"""
    result = {}
    for name, pos in (("meeting_key", 1), ("transcript_exact", 2), ("transcript_whitespace_normalized", 3)):
        holders = collections.defaultdict(list)
        for row in identities:
            holders[row[pos]].append(row)
        overlaps = [(value, rows) for value, rows in holders.items()
                    if len({r[0] for r in rows}) > 1]
        result[name] = overlaps
    return result


def cross_split_long_sentence_pairs(fingerprints):
    """将共享长句聚合到会议对，避免只报句数而漏掉重切分的同源会议。"""
    pair_counts = collections.Counter()
    for locations in fingerprints.values():
        meetings = sorted({(split, key) for split, key, _ in locations})
        for i, left in enumerate(meetings):
            for right in meetings[i + 1:]:
                if left[0] != right[0]:
                    pair_counts[(left, right)] += 1
    return pair_counts


def example_markdown(train_examples):
    lines = []
    for key, target, radius, explanation in EXAMPLES:
        record = train_examples.get(key)
        if not record:
            lines.append(f"- Train 样本 `{key}` 未找到；不输出示例。")
            continue
        sentences = record["sentences"]
        position = next((i for i, s in enumerate(sentences)
                         if isinstance(s, dict) and canonical_id(s.get("id")) == str(target)), None)
        if position is None:
            lines.append(f"- Train 样本 `{key}` 的句子 `{target}` 未找到；不输出示例。")
            continue
        window = sentences[max(0, position - radius):position + radius + 1]
        window_ids = [canonical_id(s.get("id")) for s in window if isinstance(s, dict)]
        labels = [sid for sid in window_ids if sid in record["actions"]]
        lines.extend([f"### Train `{key}`，目标句 `{target}`", "", "原文（`*` 为该窗口内原始标注）：", "", "```text"])
        for sentence in window:
            if not isinstance(sentence, dict):
                continue
            sid = canonical_id(sentence.get("id"))
            marker = "*" if sid in record["actions"] else " "
            content = str(sentence.get("s", "")).replace("\n", "\\n").replace("\r", "\\r")
            lines.append(f"{marker} [{sid}] {sentence.get('speaker', '?')}: {content}")
        lines.extend(["```", "", f"本窗口标签：`{labels}`；整场行动标签数量：{len(record['actions'])}。",
                      "", "解读：" + explanation, ""])
    return lines


def render_report(archive, structure, stats, identities, train_examples,
                  long_sentence_fingerprints, transcripts):
    overlaps = cross_split_overlaps(identities)
    repeated_long_sentences = [locations for locations in long_sentence_fingerprints.values()
                               if len({location[0] for location in locations}) > 1]
    long_sentence_pairs = cross_split_long_sentence_pairs(long_sentence_fingerprints)
    lines = ["# AliMeeting4MUG 原始数据审计（P0）", "",
             "此报告由标准库脚本从压缩包实际内容生成，原始包只读；统计日期以生成时为准。",
             "", "## 来源与文件结构", "",
             f"- 本地原件：`{archive.relative_to(PROJECT) if archive.is_relative_to(PROJECT) else archive}`",
             f"- 大小：**{format_number(archive.stat().st_size)} bytes**。",
             f"- SHA-256：`{sha256_file(archive)}`。",
             "- 文件来源：用户放入 `data/raw`。包内没有来源 URL、下载时间或发布修订号，**不能仅凭结构证明它来自官方页面**。规划中的候选来源为 [ModelScope AliMeeting4MUG](https://www.modelscope.cn/datasets/modelscope/Alimeeting4MUG)；请用户确认实际下载来源。",
             "- 容器：外层 ZIP → 三个内层 ZIP → 每个内层一个 UTF-8、Tab 分隔的 `.csv`；CSV 列为 `idx` 与 `content`，`content` 是 JSON 对象字符串。不是裸 JSON/JSONL。",
             "- ZIP CRC：外层及三个内层均经 `testzip()` 检查。脚本未解压到磁盘。",
             "", "| 成员路径 | 解压大小 bytes | 压缩后大小 bytes | 备注 / 内层 ZIP SHA-256 |", "|---|---:|---:|---|"]
    for name, size, packed, note in structure:
        lines.append(f"| `{name}` | {format_number(size)} | {format_number(packed)} | `{note}` |")
    lines.extend(["", "## 划分与标签统计", "",
                  "这里的 Test 指包中 `except_TS_test1`，没有发现 `except_TS_test2`。这表示只审计了**当前包里可见的 Test1**，不等于官方完整测试集。",
                  "", "| 划分 | CSV 行数 | 成功解析会议 | 结构/内容失败 | 标签缺失 | null | 非法标签 | 显式空标签 | 含正例会议 | 唯一正例句 | 有标签句数 | 正例比例 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for split, s in stats.items():
        failures = sum(s["parse_fail"].values())
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            split, *(format_number(x) for x in (s["rows"], s["parsed"], failures,
                s["missing_label"], s["null_label"], s["invalid_label"], s["empty_label"],
                s["positive_meetings"], s["unique_action_ids"], s["labeled_sentences"])),
            format_pct(s["unique_action_ids"], s["labeled_sentences"])))
    lines.extend(["", "**分母说明：** 正例比例 = 行动句唯一 ID 数 / 标签结构可用会议的全部句子数；缺失、null、非法标签会议不计入分母。显式空列表单独列出；其是否可视为可靠负例还需人工核对标注约定。",
                  "", "各划分正例比例都低于 1%，类别极不平衡；单报准确率会被‘全预测为非行动句’误导。P1 可在训练中调整采样，但 Dev/Test1 应保留原比例，主要看 Precision、Recall、F1 和无正例会议误报。",
                  "", "每场会议的句数、句长最小/中位/P90/最大、标签状态、跨划分共享长句数与全文 SHA-256 另见 [`meeting_inventory.csv`](meeting_inventory.csv)。该明细没有会议原文或 Test1 提示词示例。",
                  "", "| 划分 | 全部句子 | 会议句数分布 | 单句字符长度分布 | 每场行动句数分布 |",
                  "|---|---:|---|---|---|"])
    for split, s in stats.items():
        lines.append(f"| {split} | {format_number(s['sentences'])} | {distribution(s['meeting_lengths'])} | {distribution(s['sentence_lengths'])} | {distribution(s['action_per_meeting'])} |")
    lines.extend(["", "长度统计是 Python `len(str)` 的 Unicode 字符数，不是 tokenizer token 数。每场句数为 `sentences` 列表长度。",
                  "", "## 实际字段结构与多人标注", "",
                  "每行 JSON 顶层键的已观察示例包括 `meeting_key`、`sentences`、`action_ids`、`candidate`、`topic_segment_ids`、`paragraph_segment_ids`。`meeting_key` 是会议级字符串；`sentences` 是字典列表，句子包含 `id`、`speaker`、`start_time`、`end_time`、`s`。`action_ids` 是由 `{'id': 整数}` 组成的列表，引用本会议的 `sentences[].id`。",
                  "", "以下是**全量统计**的字段形状和类型：", ""])
    for split, s in stats.items():
        lines.extend([f"### {split}", "",
                      f"- `sentences` 元素键集合（前几种）：`{s['sentence_item_shapes'].most_common(5)}`；句子 ID 类型：`{dict(s['sentence_id_types'])}`。",
                      f"- `action_ids` 元素键集合：`{s['action_item_shapes'].most_common(5)}`；行动 ID 类型：`{dict(s['action_id_types'])}`。",
                      f"- 会议级 `candidate` 列表长度分布：`{dict(s['candidate_counts'])}`；话题项的 `candidate` 长度分布：`{dict(s['topic_candidate_counts'])}`。",
                      ""])
    lines.extend(["`candidate` 多个候选出现在摘要/关键词等任务，**不是**行动项的多个投票。当前压缩包 `action_ids` 若只有单份 ID 列表，无法从文件恢复每个标注员的逐人行动项判断、投票规则或分歧；只能把它当作发布的合并标签，并请用户确认标注规范。",
                  "", "## ID、一致性与跨划分重复", "",
                  "| 划分 | 会议 ID 重复行 | 句子 ID 重复次数（会议内） | 原始行动 ID 条目 | 重复行动 ID | 唯一行动 ID 匹配 | 唯一行动 ID 未匹配 | 句子元素异常 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for split, s in stats.items():
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(split,
            *(format_number(x) for x in (s["duplicate_meeting_ids"], s["duplicate_sentence_ids"],
            s["raw_action_ids"], s["duplicate_action_ids"], s["matched_action_ids"],
            s["unmatched_action_ids"], s["invalid_sentence_items"]))))
    lines.append("")
    for name, rows in overlaps.items():
        pairs = [" / ".join(f"{r[0]}:{r[1]}" for r in members[:4]) for _, members in rows[:5]]
        lines.append(f"- 跨划分 `{name}` 重复组：**{len(rows)}**；例：{'; '.join(pairs) if pairs else '无'}。")
    lines.append(f"- 跨划分完全相同的较长句子（去空白后 ≥30 字符）：**{len(repeated_long_sentences)}** 组；这可能是固定用语或局部重复，不能单独证明整场泄漏。")
    lines.append(f"- 涉及的跨划分会议对：**{len(long_sentence_pairs)}** 对。")
    for (left, right), count in long_sentence_pairs.most_common(10):
        similarity = difflib.SequenceMatcher(None, transcripts[left], transcripts[right], autojunk=False).ratio()
        lines.append(f"  - `{left[0]}:{left[1]}` ↔ `{right[0]}:{right[1]}`：共享 **{count}** 句较长原文；拼接全文字符顺序相似度 **{similarity:.3f}**（SequenceMatcher，仅供定位疑似同源）。")
    lines.extend(["", "**判定：Train `M3298` 与 Dev `M8016` 存在高度重合的会议内容，句子切分及行动 ID 不同。这个问题属于明确的训练/验证泄漏风险。P1 前应核实是否同一录音/转写版本，并将同源会议放到同一划分或从一侧排除；本阶段不改原始包和官方划分。**",
                  "", "重复检查包括相同 `meeting_key`、原文全文 SHA-256、只去掉空白后的全文 SHA-256，以及较长句子的跨划分匹配。未全面执行语义近重复或音频同源检测，因此不能据此断言其他划分完全无泄漏。`idx` 是 CSV 行索引，不应用作跨划分会议身份。",
                  "", "## 解析失败与标注异常", ""])
    for split, s in stats.items():
        lines.append(f"- {split}：解析/结构错误 `{dict(s['parse_fail'])}`；非法行动项 `{s['invalid_action_items']}`；示例 `{s['examples_of_errors']}`。")
    lines.extend(["", "缺失 `action_ids`、`null` 和非法标签都**不能**作为无行动项负样本。显式 `[]` 与缺失分开记录；若确认整个划分已完成行动项标注，才可将 `[]` 用作无正例会议。",
                  "", "## Train 原始样本：人工理解标注规则", "",
                  "以下只从 **Train** 读取原文，`*` 表示原始 `action_ids` 命中；解释是初步人工解读，不是官方定义，也不会把 Test1 内容加入提示词。", ""])
    lines.extend(example_markdown(train_examples))
    lines.extend(["## 是否适合行动句识别微调", "",
                  "从**数据结构**看，Train 有大量会议、能定位的行动句 ID，且有 Dev/Test1，具备句级检测所需的基本字段。**当前 Train/Dev 已发现同源内容风险，不能直接作为干净的训练/验证划分使用。** 正例非常稀疏；抽查中有看似背景陈述的正例及含行动线索的空标签会议。是否能做可靠监督学习，还取决于修复跨划分风险、确认空标签完整性、行动项边界一致性与人工复核。语义可靠性不能仅凭 ID 匹配率证明。",
                  "", "后续训练样本构造建议（**P1 才执行**）：",
                  "", "1. 保留官方会议级划分；不把同一场会议切出的窗口分到不同集合。",
                  "2. 用短连续句子窗口，保留会议 ID、说话人、原始句子 ID 和窗口边界；按实际 tokenizer 决定长度。",
                  "3. 每个窗口定义中心预测区，周围句子只作上下文；目标是中心区内的行动句 ID，重叠窗口不重复计分。",
                  "4. 只用 `action_ids` 结构有效且完成标注的会议；缺失和非法标签保留为待处理，不变成空标签。",
                  "5. 先核对行动项标注含义，尤其是会议原文中的建议、请求、口头安排和显式空标签会议；必要时建立小规模人工复核集。",
                  "6. 训练目标仅识别行动句；负责人、截止日期和任务是否创建需要另建标签或人工确认。",
                  "", "## 进入 P1 前需人工确认", "",
                  "- 这个本地包的下载页面、下载时间和版本；确认它就是计划使用的 AliMeeting4MUG 发布包。",
                  "- `except_TS_test1` 是否可以作为独立的可报告测试集，以及是否还有未提供的 Test2 或使用限制。",
                  "- 官方行动项标注定义与合并规则；尤其检查显式空列表会议的行动线索和若干看似只是背景句的正例。",
                  "- 是否接受先以‘句子级行动项检测’为微调目标，任务字段抽取单独评估。",
                  "- 明确处理 Train `M3298` / Dev `M8016`：确认同源关系，决定按原始来源分组重划或从一侧排除，保留原包并记录派生划分及理由。",
                  "", "## 复现", "",
                  "在项目根目录运行：`python3 scripts/audit_alimeeting4mug.py`。脚本使用标准库、读取原始 ZIP，重建本报告。若原包内容改变，报告中的 SHA-256 会改变。", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="只读审计 AliMeeting4MUG 双层 ZIP")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    args = parser.parse_args()
    archive = args.archive.resolve()
    report = args.report.resolve()
    inventory_path = args.inventory.resolve()
    if not archive.is_file():
        parser.error(f"找不到原始压缩包：{archive}")
    if archive in (report, inventory_path) or report == inventory_path:
        parser.error("原始压缩包、报告、清单的路径必须不同")
    structure, stats, identities, train_examples, inventory, long_sentence_fingerprints, transcripts = inspect_archive(archive)
    pair_counts = cross_split_long_sentence_pairs(long_sentence_fingerprints)
    pair_overlap_by_meeting = collections.Counter()
    for (left, right), count in pair_counts.items():
        pair_overlap_by_meeting[left] += count
        pair_overlap_by_meeting[right] += count
    for row in inventory:
        row["cross_split_shared_long_sentence_count"] = pair_overlap_by_meeting[(row["split"], row["meeting_key"])]
    output = render_report(archive, structure, stats, identities, train_examples,
                           long_sentence_fingerprints, transcripts)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(output, encoding="utf-8")
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    with inventory_path.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=list(inventory[0]) if inventory else ["split", "meeting_key"])
        writer.writeheader()
        writer.writerows(inventory)
    print(f"审计完成：{report}")
    print(f"会议明细：{inventory_path}")
    print(f"原始 SHA-256：{sha256_file(archive)}")
    for split, group in stats.items():
        print(f"{split}: {group['parsed']}/{group['rows']} 场，{group['unique_action_ids']} 个唯一行动 ID")


if __name__ == "__main__":
    main()
