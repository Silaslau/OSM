from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # 启用 CORS，允许跨域访问

# 数据库连接函数
def get_db():
    conn = sqlite3.connect('osm_data.db')  # 连接到数据库（如果没有，则自动创建）
    return conn

# 初始化数据库表（如果没有）
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        example_id INTEGER,
        completeness TEXT,
        correctness TEXT,
        accuracy TEXT
    )''')
    conn.commit()
    conn.close()

# 插入数据到数据库
def insert_data(example_id, completeness, correctness, accuracy):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (example_id, completeness, correctness, accuracy)
        VALUES (?, ?, ?, ?)
    ''', (example_id, completeness, correctness, accuracy))
    conn.commit()
    conn.close()

@app.route('/saveData', methods=['POST'])
def save_data():
    data = request.get_json()
    
    for example in data:
        example_id = example['exampleId']
        completeness = example['completeness']
        correctness = example['correctness']
        accuracy = example['accuracy']
        
        # 保存数据到数据库
        insert_data(example_id, completeness, correctness, accuracy)
    
    return jsonify({
        'message': '所有数据已成功保存',
        'receivedData': data
    })

if __name__ == '__main__':
    init_db()  # 初始化数据库
    app.run(debug=True, host='0.0.0.0', port=5001)