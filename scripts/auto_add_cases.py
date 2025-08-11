import argparse
import json
import re
import sys
import os
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / 'data' / 'cases.json'
DEFAULT_IMG_ROOT = ROOT / 'img'
DEFAULT_MAP_DIRS = [ROOT / 'maps', ROOT / 'annotated_maps']
DEFAULT_STATIC_DIR = ROOT / 'static'

# 便于复用 txt 解析
sys.path.append(str((Path(__file__).resolve().parent)))
try:
    from txt_to_cases import txt_to_description_array
except Exception:
    txt_to_description_array = None  # 若不可用，则描述留空


def load_cases(json_path: Path) -> List[dict]:
    if not json_path.exists():
        return []
    return json.loads(json_path.read_text(encoding='utf-8'))


def save_cases(json_path: Path, cases: List[dict]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')


def upsert_case(cases: List[dict], new_case: dict, overwrite: bool) -> List[dict]:
    new_id = str(new_case.get('id'))
    for c in cases:
        if str(c.get('id')) == new_id:
            if overwrite:
                c.update(new_case)
            return cases
    cases.append(new_case)
    return cases


def path_for_template(rel_path_from_root: Path) -> str:
    """转换为模板使用的相对路径（以 templates 目录为参照的相对路径）。"""
    templates_dir = ROOT / 'templates'
    try:
        rel = os.path.relpath(rel_path_from_root, templates_dir)
    except Exception:
        rel = str(rel_path_from_root)
    return Path(rel).as_posix()


def find_map_src(id_str: str, map_dirs: List[Path]) -> Optional[str]:
    id_token = str(id_str)
    for d in map_dirs:
        if not d.exists():
            continue
        for f in d.glob('**/*'):
            if f.is_file() and f.suffix.lower() in {'.html', '.htm'}:
                if id_token in f.stem:
                    return path_for_template(f)
    return None


def find_description(id_str: str, static_dir: Path) -> List[str]:
    if txt_to_description_array is None:
        return []
    if not static_dir.exists():
        return []
    id_token = str(id_str)
    candidates = list(static_dir.glob('**/*.txt'))
    for f in candidates:
        if id_token in f.stem:
            try:
                return txt_to_description_array(f)
            except Exception:
                continue
    return []


def parse_id_from_filename(filename: str) -> Optional[int]:
    first_part = filename.split('_')[0]
    if re.fullmatch(r'\d+', first_part):
        try:
            return int(first_part)
        except Exception:
            return None
    return None


def build_title_from_folder(folder_name: str) -> str:
    prefix = folder_name.split('_')[0].upper()
    return f"{prefix} Example"


def process_folder(img_subdir: str, json_path: Path, overwrite: bool, map_dirs: List[Path], static_dir: Path, exts: List[str]):
    folder_path = DEFAULT_IMG_ROOT / img_subdir
    if not folder_path.exists():
        raise SystemExit(f"图片目录不存在: {folder_path}")

    cases = load_cases(json_path)

    for img_file in sorted(folder_path.iterdir()):
        if not img_file.is_file():
            continue
        if img_file.suffix.lower() not in exts:
            continue

        cid = parse_id_from_filename(img_file.name)
        if cid is None:
            print(f"[WARN] 跳过非数字id文件: {img_file.name}")
            continue

        title = build_title_from_folder(folder_path.name)
        image_src = path_for_template(img_file)
        map_src = find_map_src(str(cid), map_dirs) or ''
        description = find_description(str(cid), static_dir)

        new_case = {
            'id': cid,
            'title': title,
            'image_src': image_src,
            'map_src': map_src,
            'description': description
        }

        cases = upsert_case(cases, new_case, overwrite)
        print(f"[OK] 处理 {img_file.name} -> id={cid}, title='{title}', map_src={'FOUND' if map_src else 'NONE'}, desc={'YES' if description else 'NO'}")

    cases = sorted(cases, key=lambda x: int(x.get('id', 0)))
    save_cases(json_path, cases)
    print(f"[DONE] {json_path} 已更新")


def main():
    parser = argparse.ArgumentParser(description='自动添加 img/子目录 中的图片为 cases.json 条目')
    parser.add_argument('--img-subdir', required=True, help='img 下的子目录名，例如 hk_0520 对应 img/hk_0520')
    parser.add_argument('--json', default=str(DEFAULT_JSON), help='cases.json 路径，默认 data/cases.json')
    parser.add_argument('--overwrite', action='store_true', help='若 id 已存在，是否覆盖原有条目（默认不覆盖）')
    parser.add_argument('--exts', default='.jpg,.jpeg,.png', help='图片扩展名，逗号分隔')
    parser.add_argument('--maps', default='', help='额外地图目录，逗号分隔，默认同时搜索 maps 与 annotated_maps')
    parser.add_argument('--static', default=str(DEFAULT_STATIC_DIR), help='文本描述根目录，默认 static/')
    args = parser.parse_args()

    exts = [e.strip().lower() if e.strip().startswith('.') else '.' + e.strip().lower() for e in args.exts.split(',') if e.strip()]

    map_dirs = DEFAULT_MAP_DIRS.copy()
    if args.maps:
        for p in args.maps.split(','):
            p = p.strip()
            if p:
                mp = Path(p)
                if not mp.is_absolute():
                    mp = ROOT / p
                map_dirs.append(mp)

    static_dir = Path(args.static)
    if not static_dir.is_absolute():
        static_dir = ROOT / args.static

    process_folder(args.img_subdir, Path(args.json), args.overwrite, map_dirs, static_dir, exts)


if __name__ == '__main__':
    main() 