import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT_DIR / 'data' / 'cases.json'


@dataclass
class NumberedSection:
    index: int
    title: str
    body_lines: List[str]


SECTION_START_RE = re.compile(r"^\s*(\d{1,3})\.[\s\t]*(.+?)\s*:?\s*$")


def split_into_sections(text: str) -> List[NumberedSection]:
    """Extract sections that begin with a numbered heading like '1. Title:'.
    A section ends at the first blank line after it or before next numbered heading.
    """
    lines = text.splitlines()
    sections: List[NumberedSection] = []

    current_idx: Optional[int] = None
    current_title: Optional[str] = None
    current_body: List[str] = []
    in_section = False

    def close_section():
        nonlocal current_idx, current_title, current_body, in_section
        if current_idx is not None and current_title is not None:
            # Trim trailing blank lines
            while current_body and current_body[-1].strip() == "":
                current_body.pop()
            sections.append(NumberedSection(current_idx, current_title, current_body))
        current_idx, current_title, current_body, in_section = None, None, [], False

    for raw in lines:
        line = raw.rstrip('\n')
        m = SECTION_START_RE.match(line)
        if m:
            # Starting a new section
            close_section()
            current_idx = int(m.group(1))
            current_title = m.group(2).strip()
            current_body = []
            in_section = True
            continue

        if in_section:
            # Stop at first blank line -> end section
            if line.strip() == "":
                close_section()
            else:
                current_body.append(line)

    # Close last one if still open
    if in_section:
        close_section()

    return sections


def section_to_html(section: NumberedSection) -> str:
    """Convert a section to one HTML string compatible with evaluation template.
    - Bold the name (title) and include the numeric index, e.g.,
      <strong>1. 北京穆斯林大厦 (Beijing Muslim Mansion):</strong><br>
      bullet/lines...<br>
    - Escape HTML for body content.
    """
    heading_html = f"<strong>{section.index}. {html.escape(section.title)}:</strong><br>"

    body_parts: List[str] = []
    for line in section.body_lines:
        # Preserve simple markdown-like '**Field**:' by leaving as is, only escaping non-markup
        # Strategy: escape everything, then re-bold common 'Field: xxx' patterns if desired.
        escaped = html.escape(line)
        # Make markdown '**xyz**' to <strong>xyz</strong> (optional)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        # Convert leading hyphen bullet to middot bullet visually consistent
        escaped = re.sub(r"^\s*[-•]\s*", "- ", escaped)
        body_parts.append(escaped + "<br>")

    return heading_html + "\n".join(body_parts)


def txt_to_description_array(txt_path: Path) -> List[str]:
    text = txt_path.read_text(encoding='utf-8')
    sections = split_into_sections(text)
    return [section_to_html(sec) for sec in sections]


def load_cases(json_path: Path) -> List[dict]:
    if not json_path.exists():
        return []
    return json.loads(json_path.read_text(encoding='utf-8'))


def save_cases(json_path: Path, cases: List[dict]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')


def update_case_description(cases: List[dict], case_id: int, new_desc: List[str], append: bool) -> Tuple[List[dict], bool]:
    updated = False
    for c in cases:
        if int(c.get('id', -1)) == int(case_id):
            if append and isinstance(c.get('description'), list):
                c['description'] = c['description'] + new_desc
            else:
                c['description'] = new_desc
            updated = True
            break
    return cases, updated


def infer_case_id_from_filename(path: Path) -> Optional[int]:
    # Supports formats like '12.txt' or 'case_12.txt' or 'example-12.txt'
    m = re.search(r"(\d{1,4})", path.stem)
    return int(m.group(1)) if m else None


def process_single(txt_path: Path, json_path: Path, case_id: Optional[int], append: bool) -> None:
    desc = txt_to_description_array(txt_path)
    if not desc:
        print(f"[WARN] No numbered sections found in {txt_path}")
    cases = load_cases(json_path)

    if case_id is None:
        case_id = infer_case_id_from_filename(txt_path)
    if case_id is None:
        raise ValueError("无法确定 case_id，请通过 --case-id 指定，或使用包含数字的文件名，例如 '12.txt' / 'case_12.txt'")

    cases, ok = update_case_description(cases, case_id, desc, append)
    if not ok:
        # If not found, create a new case shell
        print(f"[INFO] case_id={case_id} 不在 {json_path.name} 中，创建新条目")
        cases.append({
            'id': int(case_id),
            'title': f'Example {int(case_id)}',
            'image_src': '',
            'map_src': '',
            'description': desc
        })
        # Keep cases sorted by id
        cases = sorted(cases, key=lambda x: int(x.get('id', 0)))

    save_cases(json_path, cases)
    print(f"[OK] 已更新 case_id={case_id} 的 description，来源 {txt_path}")


def process_dir(dir_path: Path, json_path: Path, append: bool) -> None:
    cases = load_cases(json_path)
    changed = False
    for txt_file in sorted(dir_path.glob('*.txt')):
        desc = txt_to_description_array(txt_file)
        if not desc:
            print(f"[WARN] No numbered sections in {txt_file.name}, skipped")
            continue
        cid = infer_case_id_from_filename(txt_file)
        if cid is None:
            print(f"[WARN] 无法从文件名推断case id，跳过：{txt_file.name}")
            continue
        cases, _ = update_case_description(cases, cid, desc, append)
        changed = True
        print(f"[OK] 已处理 {txt_file.name} -> case_id={cid}")
    if changed:
        # Keep cases sorted
        cases = sorted(cases, key=lambda x: int(x.get('id', 0)))
        save_cases(json_path, cases)
        print(f"[OK] 批处理完成，输出 {json_path}")
    else:
        print("[INFO] 无可写入的内容")


def main():
    parser = argparse.ArgumentParser(description="Parse numbered sections in txt to update cases.json description")
    parser.add_argument('--txt', type=str, help='单个txt文件路径')
    parser.add_argument('--dir', type=str, help='包含多个txt的目录（*.txt）')
    parser.add_argument('--json', type=str, default=str(DEFAULT_JSON), help='case.json 路径，默认 data/cases.json')
    parser.add_argument('--case-id', type=int, help='目标案例ID；未提供时尝试从文件名推断')
    parser.add_argument('--append', action='store_true', help='将解析内容追加到现有description；省略则为覆盖')
    args = parser.parse_args()

    json_path = Path(args.json)

    if args.txt and args.dir:
        raise SystemExit('请二选一：--txt 或 --dir')
    if not args.txt and not args.dir:
        raise SystemExit('必须提供 --txt 或 --dir')

    if args.txt:
        process_single(Path(args.txt), json_path, args.case_id, args.append)
    else:
        process_dir(Path(args.dir), json_path, args.append)


if __name__ == '__main__':
    main() 