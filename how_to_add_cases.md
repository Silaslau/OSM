# 🚀 OSM 案例自动添加指南

## 快速开始

### 1. 基本命令
```bash
# 添加新的案例集（推荐）
python3 scripts/auto_add_cases.py --img-subdir 您的目录名 --overwrite

# 示例：添加香港数据
python3 scripts/auto_add_cases.py --img-subdir hk_0605 --overwrite
```

### 2. 准备文件结构

在运行脚本前，请确保文件按以下结构组织：

```
OSM_evaluation/
├── img/
│   └── 您的目录/              # 例如: hk_0605, pku, bj_0521
│       ├── 123_annotated.jpg   # 图片文件（ID_annotated.jpg）
│       ├── 456_annotated.jpg
│       └── ...
├── maps/
│   └── 您的目录/              # 对应的地图HTML文件
│       ├── 123.html           # ID.html 格式
│       ├── 456.html
│       └── ...
├── static/
│   └── 您的目录/              # 描述文本文件
│       ├── 123_r3.txt         # ID_r3.txt 格式
│       ├── 456_r3.txt
│       └── ...
└── data/
    └── cases.json            # 案例数据文件（自动更新）
```

## 详细参数说明

### 必需参数
- `--img-subdir`: img/ 下的子目录名
  - 例如：`hk_0605` 对应 `img/hk_0605/`

### 可选参数
- `--json`: 指定 cases.json 路径（默认：`data/cases.json`）
- `--overwrite`: 覆盖已存在的案例（推荐加上此参数）
- `--exts`: 图片扩展名（默认：`.jpg,.jpeg,.png`）
- `--maps`: 额外地图目录（默认搜索 `maps/` 和 `annotated_maps/`）
- `--static`: 文本描述根目录（默认：`static/`）

## 使用示例

### 基本使用
```bash
# 添加香港案例（推荐）
python3 scripts/auto_add_cases.py --img-subdir hk_0605 --overwrite

# 添加北京案例
python3 scripts/auto_add_cases.py --img-subdir bj_0521 --overwrite

# 添加北大案例
python3 scripts/auto_add_cases.py --img-subdir pku --overwrite

python3 scripts/auto_add_cases.py --img-subdir sh_0724 --overwrite
```

### 高级使用
```bash
# 自定义图片格式
python3 scripts/auto_add_cases.py --img-subdir my_data --exts .png,.jpg --overwrite

# 指定不同的地图目录
python3 scripts/auto_add_cases.py --img-subdir my_data --maps custom_maps --overwrite

# 不覆盖现有案例（仅添加新的）
python3 scripts/auto_add_cases.py --img-subdir my_data
```

## 文件命名规则

### 图片文件
- 格式：`ID_annotated.jpg`
- 示例：`1749082712974_annotated.jpg`
- ID 必须是数字（支持大数字如时间戳）

### 地图文件
- 格式：`ID.html`
- 示例：`1749082712974.html`
- 必须与图片的 ID 匹配

### 描述文件
- 格式：`ID_r3.txt`
- 示例：`1749082712974_r3.txt`
- 包含结构化的描述文本

## 脚本工作原理

1. **扫描图片**：在指定的 `img/子目录/` 中查找图片文件
2. **提取ID**：从文件名中提取数字ID（文件名第一个 `_` 前的数字）
3. **查找地图**：在 `maps/` 和 `annotated_maps/` 中查找对应的HTML文件
4. **解析描述**：在 `static/` 中查找对应的txt文件并解析
5. **生成案例**：创建包含所有信息的案例条目
6. **更新JSON**：将新案例添加到 `data/cases.json`

## 输出示例

脚本运行时会显示处理进度：
```
[OK] 处理 1749082712974_annotated.jpg -> id=1749082712974, title='HK Example', map_src=FOUND, desc=YES
[OK] 处理 1749082718276_annotated.jpg -> id=1749082718276, title='HK Example', map_src=FOUND, desc=YES
[DONE] /path/to/data/cases.json 已更新
```

## 注意事项

1. **备份数据**：运行前建议备份 `data/cases.json`
2. **文件命名**：确保文件按规定格式命名
3. **ID唯一性**：避免不同数据集使用相同的ID
4. **使用 --overwrite**：推荐加上此参数以确保更新
5. **检查结果**：运行后检查生成的案例是否正确

## 常见问题

### Q: 脚本提示找不到地图文件？
A: 确保 `maps/您的目录/ID.html` 文件存在且命名正确

### Q: 描述为空？
A: 检查 `static/您的目录/ID_r3.txt` 文件是否存在

### Q: ID解析失败？
A: 确保图片文件名以数字开头，如 `123_annotated.jpg`

### Q: 案例没有更新？
A: 使用 `--overwrite` 参数覆盖现有案例 