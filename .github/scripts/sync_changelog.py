#!/usr/bin/env python3
"""docs/CHANGELOG.md 최신 N개 버전을 README의 CHANGELOG 마커 사이에 주입."""
import argparse
import re
import sys
from pathlib import Path

START_MARKER = "<!-- CHANGELOG_START -->"
END_MARKER = "<!-- CHANGELOG_END -->"


def extract_latest_entries(changelog_text: str, limit: int) -> str:
    # 각 `## vX.Y.Z` 헤더부터 다음 `---` 구분선까지를 한 항목으로 간주.
    pattern = re.compile(
        r"^(## v[^\n]+\n.*?)(?=^---\s*$)",
        re.MULTILINE | re.DOTALL,
    )
    entries = [m.group(1).rstrip() for m in pattern.finditer(changelog_text)]
    if not entries:
        return ""
    return "\n\n".join(entries[:limit])


def replace_between_markers(readme_text: str, payload: str) -> str:
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    block = f"{START_MARKER}\n\n{payload}\n\n{END_MARKER}"
    if not pattern.search(readme_text):
        raise SystemExit(f"README에 {START_MARKER} / {END_MARKER} 마커가 없습니다.")
    return pattern.sub(block, readme_text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changelog", required=True, type=Path)
    parser.add_argument("--readme", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    changelog_text = args.changelog.read_text(encoding="utf-8")
    readme_text = args.readme.read_text(encoding="utf-8")

    payload = extract_latest_entries(changelog_text, args.limit)
    if not payload:
        print("CHANGELOG에서 추출할 항목이 없습니다.", file=sys.stderr)
        return 1

    new_readme = replace_between_markers(readme_text, payload)
    if new_readme != readme_text:
        args.readme.write_text(new_readme, encoding="utf-8")
        print("README 갱신 완료")
    else:
        print("README 변경 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
