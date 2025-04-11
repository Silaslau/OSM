from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # 启用 CORS，允许跨域访问

# 数据库连接函数
def get_db():
    """
    连接到 SQLite 数据库，并返回连接对象
    """
    conn = sqlite3.connect('osm_data.db')  # 连接到数据库（如果没有，则自动创建）
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    return conn

# 初始化数据库表（如果没有）
def init_db():
    """
    初始化数据库表（如果没有则创建）
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            example_id INTEGER,
            completeness TEXT,
            correctness TEXT,
            accuracy TEXT
        )''')
        conn.commit()

# 插入数据到数据库
def insert_data(example_id, completeness, correctness, accuracy):
    """
    将数据插入到 feedback 表中
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (example_id, completeness, correctness, accuracy)
            VALUES (?, ?, ?, ?)
        ''', (example_id, completeness, correctness, accuracy))
        conn.commit()

# 路由：接收 POST 请求并保存数据
@app.route('/saveData', methods=['POST'])
def save_data():
    """
    处理保存数据的请求，将数据保存到数据库中
    """
    try:
        data = request.get_json()  # 获取 POST 请求中的 JSON 数据
        
        # 验证数据格式是否正确
        if not isinstance(data, list):  # 确保数据是一个列表
            return jsonify({'error': 'Invalid data format. Expected an array of data.'}), 400
        
        for example in data:
            # 验证每个数据项是否包含所需字段
            if 'exampleId' not in example or 'completeness' not in example or \
               'correctness' not in example or 'accuracy' not in example:
                return jsonify({'error': 'Missing required fields in data.'}), 400
            
            example_id = example['exampleId']
            completeness = example['completeness']
            correctness = example['correctness']
            accuracy = example['accuracy']
            
            # 保存数据到数据库
            insert_data(example_id, completeness, correctness, accuracy)

        return jsonify({
            'message': '所有数据已成功保存',
            'receivedData': data
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()  # 初始化数据库
    app.run(debug=True, host='0.0.0.0', port=5001)