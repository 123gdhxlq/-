#!/usr/bin/env python3
"""检查正文中的明显历史穿帮词和未完成标记。

这是低成本的第一道门，不能代替人工考据。退出码为 0 表示没有阻断性问题。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript" / "正文"
LEDGER_PATH = ROOT / "docs" / "历史事实台账.json"
CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}
MIN_BODY_CHARS = 1000


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"错误：找不到历史事实台账：{LEDGER_PATH}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"错误：历史事实台账不是有效 JSON：{exc}")


def find_line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def chinese_number(value: str) -> int | None:
    """把章节标题中的中文数字转换成整数，例如“十”“二十三”。"""
    if not value or any(char not in CHINESE_DIGITS and char not in CHINESE_UNITS for char in value):
        return None
    total = 0
    current = 0
    for char in value:
        if char in CHINESE_DIGITS:
            current = CHINESE_DIGITS[char]
            continue
        unit = CHINESE_UNITS[char]
        if current == 0:
            current = 1
        total += current * unit
        current = 0
    return total + current


def scan_file(path: Path, forbidden: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    issues: list[str] = []

    lines = text.splitlines()
    body = "".join(lines[1:]) if len(lines) > 1 else ""
    body_chars = len(re.sub(r"\s", "", body))
    if body_chars < MIN_BODY_CHARS:
        issues.append(
            f"{path.relative_to(ROOT)}:1: 正文仅{body_chars}字，少于最低要求{MIN_BODY_CHARS}字"
        )

    for term in forbidden:
        for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            issues.append(f"{path.relative_to(ROOT)}:{find_line(text, match.start())}: 禁止词“{term}”")

    for marker in ("TODO", "TBD", "待补", "待填写"):
        for match in re.finditer(re.escape(marker), text, flags=re.IGNORECASE):
            issues.append(f"{path.relative_to(ROOT)}:{find_line(text, match.start())}: 未完成标记“{marker}”")

    heading = re.search(r"^# 第(.+?)章", text, flags=re.MULTILINE)
    if not heading:
        issues.append(f"{path.relative_to(ROOT)}:1: 缺少“# 第X章”章节标题")
    else:
        filename_number = re.match(r"(\d+)-", path.name)
        heading_number = chinese_number(heading.group(1))
        if filename_number and heading_number is not None:
            expected = int(filename_number.group(1))
            if expected != heading_number:
                issues.append(
                    f"{path.relative_to(ROOT)}:1: 文件编号为第{expected}章，标题却写成第{heading_number}章"
                )

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="检查小说正文的明显历史与编辑穿帮问题")
    parser.add_argument("--json", action="store_true", dest="as_json", help="以 JSON 输出报告")
    args = parser.parse_args()

    ledger = load_ledger()
    files = sorted(MANUSCRIPT_DIR.rglob("*.md")) if MANUSCRIPT_DIR.exists() else []
    issues: list[str] = []
    for path in files:
        issues.extend(scan_file(path, ledger.get("forbidden_in_manuscript", [])))

    numbered_files = []
    for path in files:
        match = re.match(r"(\d+)-", path.name)
        if match:
            numbered_files.append((int(match.group(1)), path))
    numbers = [number for number, _ in numbered_files]
    if len(numbers) != len(set(numbers)):
        issues.append("正文文件编号重复")
    if numbers:
        expected_numbers = set(range(1, max(numbers) + 1))
        missing = sorted(expected_numbers - set(numbers))
        if missing:
            issues.append("正文文件编号缺失：" + ", ".join(str(number) for number in missing))

    report = {
        "manuscript_files": len(files),
        "blocking_issues": issues,
        "status": "PASS" if not issues else "FAIL",
    }

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("历史与连续性自动检查")
        print(f"正文文件：{len(files)}")
        if issues:
            print("发现问题：")
            print("\n".join(f"- {issue}" for issue in issues))
            print("结果：FAIL")
        else:
            print("发现问题：0")
            print("结果：PASS")

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
