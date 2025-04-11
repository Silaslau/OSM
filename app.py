from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__, template_folder='.')
CORS(app)

# 从环境变量中读取数据库地址（Render 自动提供）
DATABASE_URL = os.environ.get("DATABASE_URL")

# 建立数据库连接
def get_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# 初始化表
def init_db():
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

# 插入数据
def insert_data(example_id, completeness, correctness, accuracy):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO feedback (example_id, completeness, correctness, accuracy)
                VALUES (%s, %s, %s, %s)
            ''', (example_id, completeness, correctness, accuracy))
            conn.commit()

@app.route('/saveData', methods=['POST'])
def save_data():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({'error': 'Invalid data format'}), 400

        for item in data:
            insert_data(
                item['exampleId'],
                item['completeness'],
                item['correctness'],
                item['accuracy']
            )
        return jsonify({'message': '所有数据已成功保存', 'receivedData': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/viewData')
def view_data():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)