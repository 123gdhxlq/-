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


def load_ledger() -> dict:
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"错误：找不到历史事实台账：{LEDGER_PATH}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"错误：历史事实台账不是有效 JSON：{exc}")


def find_line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def scan_file(path: Path, forbidden: list[str]) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    issues: list[str] = []

    for term in forbidden:
        for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            issues.append(f"{path.relative_to(ROOT)}:{find_line(text, match.start())}: 禁止词“{term}”")

    for marker in ("TODO", "TBD", "待补", "待填写"):
        for match in re.finditer(re.escape(marker), text, flags=re.IGNORECASE):
            issues.append(f"{path.relative_to(ROOT)}:{find_line(text, match.start())}: 未完成标记“{marker}”")

    if not re.search(r"^# 第.+章", text, flags=re.MULTILINE):
        issues.append(f"{path.relative_to(ROOT)}:1: 缺少“# 第X章”章节标题")

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
