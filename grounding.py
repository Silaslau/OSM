import os
import base64
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# === 将图片转换为 Base64 格式 ===
def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# === 调用 Qwen-VL via OpenAI SDK 接口 ===
def call_qwen_vl_sdk(image_path, description, api_key):
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    image_base64 = image_to_base64(image_path)
    data_url = f"data:image/jpeg;base64,{image_base64}"

    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": f"""请根据下列描述，在图片中识别对应区域，并返回 JSON 格式的边界框数据：
            
描述：
{description}

输出格式如下：
{{
  "objects": [
    {{
      "label": "对象名称",
      "bounding_box": [x1, y1, x2, y2]
    }}
  ]
}}
"""},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]}
    ]

    response = client.chat.completions.create(
        model="qwen-vl-plus",
        messages=messages
    )
    return response.choices[0].message.content

# === 绘制边界框和标签 ===
def draw_boxes_on_image(image_path, objects, output_path):
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    for obj in objects:
        label = obj["label"]
        box = obj["bounding_box"]
        draw.rectangle(box, outline="red", width=2)
        draw.rectangle([box[0], box[1], box[0]+8+len(label)*6, box[1]+18], fill="white")
        draw.text((box[0]+2, box[1]+2), label, fill="red", font=font)

    image.save(output_path)
    print(f"✅ 已保存标注图像：{output_path}")

# === 主流程 ===
def main():
    image_path = "Jockey_hall_S.JPG"
    output_path = "Jockey_hall_marked.jpg"
    description = '''
    1. Vegetation (Forest) – Hill Slope: ...
    2. Vegetation (Forest) – Hilly Terrain: ...
    3. Jockey Club Global Graduate Tower: ...
    4. Jockey Club i-Village: ...
    5. HKUST Lee Shau Kee Business Building: ...
    '''
    api_key = "sk-f167c63bb9dc4263a853189b580f37a2"

    try:
        # Step 1: 调用百炼接口（OpenAI SDK）
        raw_response = call_qwen_vl_sdk(image_path, description, api_key)
        print("✅ API返回原始内容：\n", raw_response)

        # Step 2: 提取 JSON（从返回字符串中解析）
        import json, re
        json_str = re.search(r"\{[\s\S]*\}", raw_response).group()
        result = json.loads(json_str)

        objects = result.get("objects", [])
        if not objects:
            print("⚠️ 未检测到任何对象")
            return

        # Step 3: 绘图
        draw_boxes_on_image(image_path, objects, output_path)

    except Exception as e:
        print("❌ 出错了:", e)

if __name__ == "__main__":
    main()