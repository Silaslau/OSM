from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
try:
    import psycopg2  # 可选，仅在有 DB_URL 时使用
except Exception:
    psycopg2 = None
import sqlite3
import os
import json
import random
from pathlib import Path
from flask import send_from_directory

app = Flask(__name__, template_folder='.')
CORS(app)

# 从环境变量中读取数据库地址（Render 自动提供）
DATABASE_URL = os.environ.get("DB_URL")
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'data' / 'cases.json'

# 建立数据库连接
def get_db():
    if DATABASE_URL and psycopg2 is not None:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # 本地调试使用 SQLite
        db_path = BASE_DIR / 'osm_data.db'
        conn = sqlite3.connect(str(db_path))
    return conn

# 初始化表
def init_db():
    if DATABASE_URL and psycopg2 is not None:
        # PostgreSQL
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        example_id INTEGER,
                        completeness TEXT,
                        correctness TEXT,
                        accuracy TEXT
                    )
                ''')
                conn.commit()
    else:
        # SQLite
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                example_id INTEGER,
                completeness TEXT,
                correctness TEXT,
                accuracy TEXT
            )
        ''')
        conn.commit()
        conn.close()

# 插入数据
def insert_data(example_id, completeness, correctness, accuracy):
    with get_db() as conn:
        with conn.cursor() as cur:
            if DATABASE_URL and psycopg2 is not None:
                # PostgreSQL
                cur.execute('''
                    INSERT INTO feedback (example_id, completeness, correctness, accuracy)
                    VALUES (%s, %s, %s, %s)
                ''', (example_id, completeness, correctness, accuracy))
            else:
                # SQLite
                cur.execute('''
                    INSERT INTO feedback (example_id, completeness, correctness, accuracy)
                    VALUES (?, ?, ?, ?)
                ''', (example_id, completeness, correctness, accuracy))
            conn.commit()

@app.route('/saveData', methods=['POST'])
def save_data():
    data = request.json
    print(f"收到数据: {data}")
    
    for item in data:
        example_id = item.get('example_id')
        completeness = item.get('completeness')
        correctness = item.get('correctness')
        accuracy = item.get('accuracy')
        
        if DATABASE_URL and psycopg2 is not None:
            # PostgreSQL
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO feedback (example_id, completeness, correctness, accuracy)
                        VALUES (%s, %s, %s, %s)
                    ''', (example_id, completeness, correctness, accuracy))
                    conn.commit()
        else:
            # SQLite
            conn = get_db()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO feedback (example_id, completeness, correctness, accuracy)
                VALUES (?, ?, ?, ?)
            ''', (example_id, completeness, correctness, accuracy))
            conn.commit()
            conn.close()
    
    return jsonify({"status": "success", "message": "数据保存成功"})

@app.route('/getFeedback', methods=['GET'])
def get_feedback():
    try:
        if DATABASE_URL and psycopg2 is not None:
            # PostgreSQL
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM feedback")
                    rows = cur.fetchall()
        else:
            # SQLite
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM feedback")
            rows = cur.fetchall()
            conn.close()
        
        return jsonify({"status": "success", "data": rows})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/viewData')
def view_data():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if DATABASE_URL and psycopg2 is not None:
                    # PostgreSQL
                    cur.execute("SELECT * FROM feedback")
                else:
                    # SQLite
                    cur.execute("SELECT * FROM feedback")
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                results = [dict(zip(columns, row)) for row in rows]
                return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/osm')
def osm():
    return render_template('templates/osm.html')

# ===== 新增：基于 JSON 的评测页面 =====
def load_all_cases():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/evaluation')
def evaluation():
    try:
        all_cases = load_all_cases()
        if not all_cases:
            # 没有数据则直接渲染空页提示
            return render_template('templates/evaluation.html', cases=[])
        # 读取参数 n，默认 15；可选 seed 以便复现实验
        n = request.args.get('n', default=15, type=int)
        seed = request.args.get('seed', default=None, type=int)
        if seed is not None:
            random.seed(seed)
        selected = random.sample(all_cases, k=min(n, len(all_cases)))
        return render_template('templates/evaluation.html', cases=selected)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== 新增：简化版页面（前端从 cases.json 抽样） =====
@app.route('/osm_simple')
def osm_simple():
    return render_template('templates/osm_simple.html')

# ===== 新增：静态资源路由（供前端直接访问） =====
@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory(BASE_DIR / 'data', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(BASE_DIR / 'images', filename)

@app.route('/img/<path:filename>')
def serve_img(filename):
    return send_from_directory(BASE_DIR / 'img', filename)

@app.route('/maps/<path:filename>')
def serve_maps(filename):
    return send_from_directory(BASE_DIR / 'maps', filename)

@app.route('/annotated_maps/<path:filename>')
def serve_annotated_maps(filename):
    return send_from_directory(BASE_DIR / 'annotated_maps', filename)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

    # PORT=8000 python3 app.py                                            
    # http://127.0.0.1:8000/osm_simple