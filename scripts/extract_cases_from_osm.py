import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OSM_HTML = ROOT / 'templates' / 'osm.html'
OUT_JSON = ROOT / 'data' / 'cases.json'


def extract_blocks(html: str):
    blocks = []
    pattern = re.compile(r'<div class="example-card" id="example-(\d+)">', re.IGNORECASE)
    matches = list(pattern.finditer(html))
    for idx, m in enumerate(matches):
        ex_id = int(m.group(1))
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else html.find('<!-- Submit button -->')
        if end == -1:
            end = len(html)
        blocks.append((ex_id, html[start:end]))
    return blocks


def extract_first(regex: str, text: str):
    m = re.search(regex, text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def extract_case(ex_id: int, segment: str):
    # title: 第一个 <h2> 的内容，若不存在，回退为 Example {id}
    titles = re.findall(r'<h2>(.*?)</h2>', segment, re.IGNORECASE | re.DOTALL)
    title = clean_text(titles[0]) if titles else f"Example {ex_id}"

    # image: 段内第一个 <img src="...">
    image_src = extract_first(r'<img[^>]+src="([^"]+)"', segment)

    # iframe map: 段内第一个 <iframe src="...">
    map_src = extract_first(r'<iframe[^>]+src="([^"]+)"', segment)

    # text-box: 捕获其内部 HTML
    tb_start = segment.find('<div class="text-box">')
    description_items = []
    if tb_start != -1:
        tb_end = segment.find('</div>', tb_start)
        text_box_html = segment[tb_start:tb_end]

        # 找到每个 <strong> ... </strong> 块，以及其后续到下一个 <strong> 前的内容
        strong_iter = list(re.finditer(r'<strong>(.*?)</strong>', text_box_html, re.IGNORECASE | re.DOTALL))
        for i, sm in enumerate(strong_iter):
            heading = clean_text(sm.group(1))
            if heading.lower().startswith('picture description'):
                # 跳过标题
                continue
            content_start = sm.start()
            content_end = strong_iter[i + 1].start() if i + 1 < len(strong_iter) else len(text_box_html)
            chunk_html = text_box_html[content_start:content_end].strip()
            # 保留 HTML（含 <strong> 与 <br>），前端模板会 |safe 渲染
            if chunk_html:
                description_items.append(chunk_html)

    return {
        'id': ex_id,
        'title': title,
        'image_src': image_src,
        'map_src': map_src,
        'description': description_items
    }


def main():
    html = OSM_HTML.read_text(encoding='utf-8')
    cases = []
    for ex_id, seg in extract_blocks(html):
        case = extract_case(ex_id, seg)
        cases.append(case)

    # 按 id 排序
    cases.sort(key=lambda x: x['id'])

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {len(cases)} cases to {OUT_JSON}")


if __name__ == '__main__':
    main() 