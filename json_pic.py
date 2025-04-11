from PIL import Image, ImageDraw, ImageFont

# 图片文件路径
name = "Jockey_hall_S"
# name = "Shaw_E"
# name = "Staff_15_160"
# name = "Staff_hall_110"
# name = "Tennis_5_E"
image_path = f"{name}.jpg"
annotation_size = (1148, 861)

# 标注信息
annotations = {
    "objects": [
        {
            "label": "Vegetation (Forest) – Hill Slope",
            "bounding_box": [0, 250, 400, 650]
        },
        {
            "label": "Vegetation (Forest) – Hilly Terrain",
            "bounding_box": [700, 180, 1148, 650]
        },
        {
            "label": "Jockey Club Global Graduate Tower",
            "bounding_box": [0, 0, 180, 500]
        },
        {
            "label": "Jockey Club i-Village",
            "bounding_box": [180, 290, 650, 600]
        },
        {
            "label": "HKUST Lee Shau Kee Business Building",
            "bounding_box": [700, 0, 1148, 500]
        }
    ]
    }

# annotations = {
#   "objects": [
#     {
#       "label": "HKUST Senior Staff Quarters Block 16",
#       "bounding_box": [0, 0, 450, 861]
#     },
#     {
#       "label": "Leisure Garden",
#       "bounding_box": [0, 500, 450, 861]
#     }
#   ]
# }

# Tennis 5
# annotations ={
#   "objects": [
#     {
#       "label": "Cheng Yu Tung Building",
#       "bounding_box": [0, 108, 759, 574]
#     },
#     {
#       "label": "Tennis Courts No.5 & 6",
#       "bounding_box": [598, 408, 1147, 574]
#     },
#     {
#       "label": "Shaw Auditorium",
#       "bounding_box": [759, 295, 1147, 574]
#     }
#   ]
# }

# Shaw
# annotations = {
#   "objects": [
#     {
#       "label": "Cheng Yu Tung Building",
#       "bounding_box": [0, 0, 450, 450]
#     },
#     {
#       "label": "Shaw Auditorium",
#       "bounding_box": [300, 0, 1148, 600]
#     }
#   ]
# } 

# Staff_110
# annotations = {
#   "objects": [
#     {
#       "label": "Dense Trees (Natural Wood)",
#       "bounding_box": [0, 0, 400, 861]
#     },
#     {
#       "label": "HKUST Senior Staff Quarters Block 15",
#       "bounding_box": [400, 0, 700, 861]
#     },
#     {
#       "label": "HKUST Senior Staff Quarters Block 12",
#       "bounding_box": [700, 0, 1148, 861]
#     }
#   ]
# }


# 打开图像（不改变原始尺寸）
image = Image.open(image_path).convert("RGB")
real_width, real_height = image.size
print(f"size: {image.size}")
draw = ImageDraw.Draw(image)

# 设置字体
try:
    font = ImageFont.truetype("arial.ttf", size=64)
except:
    font = ImageFont.load_default(size=64)

text_color = (255, 255, 255)
bg_color = (0, 0, 0)

# 生成多种颜色用于不同对象
color_palette = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 165, 0),    # Orange
    (128, 0, 128),    # Purple
    (0, 255, 255),    # Cyan
    (255, 192, 203),  # Pink
]

# 计算缩放比例
scale_x = real_width / annotation_size[0]
scale_y = real_height / annotation_size[1]

# 遍历对象并绘制
for idx, obj in enumerate(annotations["objects"]):
    label = obj["label"]
    bbox = obj["bounding_box"]

    # 坐标缩放
    x1 = int(bbox[0] * scale_x)
    y1 = int(bbox[1] * scale_y)
    x2 = int(bbox[2] * scale_x)
    y2 = int(bbox[3] * scale_y)
    scaled_bbox = [x1, y1, x2, y2]

    # 边框颜色
    box_color = color_palette[idx % len(color_palette)]

    # 绘制边界框
    draw.rectangle(scaled_bbox, outline=box_color, width=9)

    # 计算文字尺寸
    text_size = draw.textbbox((0, 0), label, font=font)
    text_width = text_size[2] - text_size[0]
    text_height = text_size[3] - text_size[1]

    # 文本显示位置
    text_x = x1
    text_y = max(0, y1 - text_height - 4*scale_y)

    # 绘制黑色背景
    draw.rectangle(
    [text_x, text_y, text_x + text_width + 24*scale_x, text_y + text_height + 16*scale_y],
    fill=bg_color
)
    draw.text((text_x + 12*scale_x, text_y + 8*scale_y), label, fill=text_color, font=font)

# 保存输出图像
output_path = f"{name}_annoted.jpg"
image.save(output_path)

print(f"✅ 标记后的图片（保持原始尺寸）已保存到: {output_path}")