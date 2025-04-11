from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os  # ✅ 添加这个以支持 Render 平台动态端口

app = Flask(__name__, template_folder='.')  
CORS(app)  # ✅ 允许跨域访问

# -------------------- 数据库连接 --------------------

def get_db():
    conn = sqlite3.connect('osm_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                example_id INTEGER,
                completeness TEXT,
                correctness TEXT,
                accuracy TEXT
            )
        ''')
        conn.commit()

def insert_data(example_id, completeness, correctness, accuracy):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (example_id, completeness, correctness, accuracy)
            VALUES (?, ?, ?, ?)
        ''', (example_id, completeness, correctness, accuracy))
        conn.commit()

# -------------------- 接口 --------------------

@app.route('/saveData', methods=['POST'])
def save_data():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({'error': 'Invalid data format. Expected an array of data.'}), 400
        
        for example in data:
            if 'exampleId' not in example or 'completeness' not in example or \
               'correctness' not in example or 'accuracy' not in example:
                return jsonify({'error': 'Missing required fields in data.'}), 400

            insert_data(
                example['exampleId'],
                example['completeness'],
                example['correctness'],
                example['accuracy']
            )

        return jsonify({'message': '所有数据已成功保存', 'receivedData': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------- 页面路由（可选） --------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/osm')
def osm():
    return render_template('templates/osm.html')  # ✅ 修正路径（GitHub Pages 只用静态文件就够）

# -------------------- 启动服务 --------------------

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))  # ✅ Render 会提供环境变量 PORT
    app.run(host='0.0.0.0', port=port)