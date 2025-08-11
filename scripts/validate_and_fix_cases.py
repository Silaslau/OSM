import json
import re
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
CASES_JSON = ROOT / 'data' / 'cases.json'
IMG_DIRS = [ROOT / 'images', ROOT / 'img']
MAP_DIRS = [ROOT / 'maps', ROOT / 'annotated_maps']


def normalize_rel_prefix(p: str) -> str:
    # 去掉所有开头的 '../'
    while p.startswith('../'):
        p = p[3:]
    # 去掉开头的 './'
    while p.startswith('./'):
        p = p[2:]
    # 去掉开头的 '/'
    p = p.lstrip('/')
    return p


def fix_image_path(path_str: str) -> Tuple[str, bool]:
    original = path_str
    p = normalize_rel_prefix(path_str)
    # 修正常见前缀错误
    p = re.sub(r'^image/', 'images/', p)  # image -> images
    p = re.sub(r'^images/ust/', 'images/', p)  # 去掉 ust 子目录

    # 先尝试在 images/ 下找
    cand = ROOT / p
    if cand.exists():
        return '/' + p, '/' + p != original

    # 若以 images/ 开头但不存在，尝试从 img/ 映射
    if p.startswith('images/'):
        tail = p.split('images/', 1)[1]
        for img_root in IMG_DIRS:
            alt = img_root / tail
            if alt.exists():
                return '/' + str(alt.relative_to(ROOT)), True

    # 若不以 images/ 开头，尝试在两类图片目录中寻找同名文件
    name = Path(p).name
    for img_root in IMG_DIRS:
        alt = img_root / name
        if alt.exists():
            return '/' + str(alt.relative_to(ROOT)), True

    # 原样返回标准化结果
    return '/' + p, '/' + p != original


def find_map_by_id(map_id: str) -> str:
    # 在 maps 与 annotated_maps 中寻找包含 id 的 html（优先 maps 再 annotated_maps）
    for d in MAP_DIRS:
        for html in d.rglob('*.html'):
            if map_id in html.name:
                return '/' + str(html.relative_to(ROOT))
    return ''


def fix_map_src(path_str: str) -> Tuple[str, bool]:
    original = path_str
    p = normalize_rel_prefix(path_str)
    cand = ROOT / p
    if cand.exists():
        return '/' + p, '/' + p != original

    # 不存在则用文件名中的 id 重配
    base = Path(p).name
    id_part = base.split('_')[0]
    map_id = id_part if id_part.isdigit() else base.replace('.html', '')
    new_path = find_map_by_id(map_id)
    if new_path:
        return new_path, True
    return '/' + p, '/' + p != original


def main():
    cases: List[dict] = json.loads(CASES_JSON.read_text(encoding='utf-8'))
    changed = False
    report: List[str] = []

    for c in cases:
        # 修复 image_src
        if 'image_src' in c and c['image_src']:
            new_img, img_changed = fix_image_path(c['image_src'])
            if img_changed:
                report.append(f"id={c.get('id')} image_src: {c['image_src']} -> {new_img}")
                c['image_src'] = new_img
                changed = True
        # 修复 map_src
        if 'map_src' in c and c['map_src']:
            new_map, map_changed = fix_map_src(c['map_src'])
            if map_changed:
                report.append(f"id={c.get('id')} map_src: {c['map_src']} -> {new_map}")
                c['map_src'] = new_map
                changed = True

    if changed:
        CASES_JSON.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    print("\n".join(report) if report else "No changes needed.")


if __name__ == '__main__':
    main() 