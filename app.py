"""\
后端服务（Flask）
- 提供 OSM 评测页面与静态资源服务
- 读取 `data/cases.json` 进行数据驱动渲染
- 采集用户反馈并写入数据库（Render 上优先 Postgres，本地回退 SQLite）
- 针对 Render 环境做了连接重试、keepalive、健康检查与轻量迁移
"""
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
import time
from pathlib import Path
from flask import send_from_directory
from flask import redirect, render_template

app = Flask(__name__, template_folder='.')
CORS(app)

# 统一获取数据库 URL（兼容 Render 常见变量名）
def _resolve_db_url() -> str:
    """解析数据库连接 URL。
    - 兼容 Render 常见变量：DATABASE_INTERNAL_URL（推荐）、DATABASE_URL、DB_URL、POSTGRES_URL/URI。
    - 存在即返回第一优先的值；均不存在返回空字符串，表示走 SQLite 本地开发模式。
    """
    for key in [
        'DATABASE_URL',            # Render 外部连接 URL
        'DATABASE_INTERNAL_URL',   # Render 内网连接 URL（推荐同区域）
        'DB_URL',                  # 你本地之前使用的变量
        'POSTGRES_URL', 'POSTGRES_URI'
    ]:
        val = os.environ.get(key)
        if val:
            return val
    return ''

DATABASE_URL = _resolve_db_url()
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / 'data' / 'cases.json'

# 建立数据库连接（带重试与 keepalive）
def get_db():
    """获取数据库连接。
    - 若存在 Postgres 配置且安装了 psycopg2，则以 require SSL 连接，启用 keepalive；失败做 5 次指数退避重试。
    - 否则回退到本地 SQLite（仅用于本地开发）。
    """
    if DATABASE_URL and psycopg2 is not None:
        last_err = None
        for attempt in range(5):
            try:
                conn = psycopg2.connect(
                    DATABASE_URL,
                    sslmode='require',
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=5,
                )
                return conn
            except Exception as e:
                last_err = e
                # 指数退避重试：0.5s, 1s, 2s, 4s, 8s
                time.sleep(0.5 * (2 ** attempt))
        # 多次重试失败，抛出以便 Render 看到明确错误
        raise last_err
    else:
        # 本地调试使用 SQLite（Render 线上不会走到这里）
        db_path = BASE_DIR / 'osm_data.db'
        conn = sqlite3.connect(str(db_path))
        return conn

def _pg_migrate_example_id_bigint(conn):
    """将 feedback.example_id 由 INTEGER 迁移为 BIGINT（幂等）。
    - 解决 13 位时间戳等大整数写入时的溢出问题。
    - 若已为 BIGINT 或迁移失败，仅记录日志不阻断启动。
    """
    try:
        with conn.cursor() as cur:
            # 将 example_id 升级为 BIGINT，已是 BIGINT 时不会报错
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='feedback' AND column_name='example_id' AND data_type='integer'
                    ) THEN
                        ALTER TABLE feedback ALTER COLUMN example_id TYPE BIGINT;
                    END IF;
                END$$;
            """)
            conn.commit()
    except Exception as e:
        # 迁移失败不阻塞启动，仅记录
        print(f"[WARN] migrate example_id->BIGINT failed: {e}")

def _ensure_username_column(conn):
    """为 feedback 表增加 username 列（幂等）。
    - PostgreSQL: 使用 IF NOT EXISTS。
    - SQLite: 直接尝试 ADD COLUMN，若已存在则忽略错误。
    """
    try:
        if DATABASE_URL and psycopg2 is not None:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS username TEXT")
                conn.commit()
        else:
            cur = conn.cursor()
            try:
                cur.execute("ALTER TABLE feedback ADD COLUMN username TEXT")
                conn.commit()
            except Exception:
                # 已存在列时忽略
                pass
    except Exception as e:
        print(f"[WARN] ensure username column failed: {e}")

def _ensure_matching_column(conn):
    """为 feedback 表增加 matching 列（幂等）。
    - PostgreSQL: 使用 IF NOT EXISTS。
    - SQLite: 直接尝试 ADD COLUMN，若已存在则忽略错误。
    """
    try:
        if DATABASE_URL and psycopg2 is not None:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS matching TEXT")
                conn.commit()
        else:
            cur = conn.cursor()
            try:
                cur.execute("ALTER TABLE feedback ADD COLUMN matching TEXT")
                conn.commit()
            except Exception:
                # 已存在列时忽略
                pass
    except Exception as e:
        print(f"[WARN] ensure matching column failed: {e}")

# 初始化表（分别支持 PG 与 SQLite）
def init_db():
    """初始化数据库表结构。
    - Postgres：创建 feedback 表并保证 example_id 为 BIGINT；随后尝试做幂等迁移。
    - SQLite：创建 feedback 表（SQLite INTEGER 为 64 位，足够大）。
    """
    if DATABASE_URL and psycopg2 is not None:
        # PostgreSQL
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS feedback (
                        id SERIAL PRIMARY KEY,
                        example_id BIGINT,
                        completeness TEXT,
                        correctness TEXT,
                        accuracy TEXT,
                        matching TEXT,
                        username TEXT
                    )
                ''')
                conn.commit()
            # 尝试迁移旧表结构中的 example_id: INTEGER -> BIGINT
            _pg_migrate_example_id_bigint(conn)
            # 确保存在 username 列
            _ensure_username_column(conn)
            # 确保存在 matching 列
            _ensure_matching_column(conn)
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
                accuracy TEXT,
                matching TEXT,
                username TEXT
            )
        ''')
        conn.commit()
        # 旧表无 username 时补充
        _ensure_username_column(conn)
        # 旧表无 matching 时补充
        _ensure_matching_column(conn)
        conn.close()

# 插入数据
def insert_data(example_id, completeness, correctness, accuracy, username=None):
    """通用插入函数：写入一条反馈记录。"""
    with get_db() as conn:
        with conn.cursor() as cur:
            if DATABASE_URL and psycopg2 is not None:
                # PostgreSQL
                cur.execute('''
                    INSERT INTO feedback (example_id, completeness, correctness, accuracy, username)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (example_id, completeness, correctness, accuracy, username))
            else:
                # SQLite
                cur.execute('''
                    INSERT INTO feedback (example_id, completeness, correctness, accuracy, username)
                    VALUES (?, ?, ?, ?, ?)
                ''', (example_id, completeness, correctness, accuracy, username))
            conn.commit()

@app.route('/saveData', methods=['POST'])
def save_data():
    """接收前端提交的多条评测结果并入库。
    - 兼容字段：example_id / exampleId / id（优先），其余为 completeness/correctness/accuracy。
    - 对缺失或非数字 id 的记录跳过并记录警告。
    """
    data = request.json
    print(f"收到数据: {data}")
    
    for item in data:
        # 同时兼容 example_id 与 exampleId
        raw_id = item.get('example_id', item.get('exampleId', item.get('id')))
        try:
            example_id = int(raw_id) if raw_id is not None else None
        except Exception:
            example_id = None
        completeness = item.get('completeness')
        correctness = item.get('correctness')
        accuracy = item.get('accuracy')
        username = item.get('username')
        matching = item.get('matching')
        
        if example_id is None:
            print(f"[WARN] 跳过一条因缺少 example_id 的记录: {item}")
            continue
        
        if DATABASE_URL and psycopg2 is not None:
            # PostgreSQL
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO feedback (example_id, completeness, correctness, accuracy, matching, username)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (example_id, completeness, correctness, accuracy, matching, username))
                    conn.commit()
        else:
            # SQLite
            conn = get_db()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO feedback (example_id, completeness, correctness, accuracy, matching, username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (example_id, completeness, correctness, accuracy, matching, username))
            conn.commit()
            conn.close()
    
    return jsonify({"status": "success", "message": "数据保存成功"})

@app.route('/getFeedback', methods=['GET'])
def get_feedback():
    """返回 feedback 全表数据（调试用途）。"""
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
    """以 JSON 形式返回 feedback（包含列名），便于前端或导出。"""
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

@app.route('/exportData')
def export_data():
    """导出 feedback 数据为 CSV 格式。"""
    try:
        import csv
        import io
        
        with get_db() as conn:
            with conn.cursor() as cur:
                if DATABASE_URL and psycopg2 is not None:
                    cur.execute("SELECT * FROM feedback ORDER BY id")
                else:
                    cur.execute("SELECT * FROM feedback ORDER BY id")
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
        
        # 创建 CSV 内容
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)  # 写入列名
        writer.writerows(rows)    # 写入数据
        
        # 返回 CSV 响应
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=feedback_data.csv'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def root_redirect():
    """站点首页：展示加载动画的 index.html，随后前端跳转到 /osm_simple。"""
    return render_template('index.html')

@app.route('/index.html')
def index_redirect():
    """兼容 /index.html 访问入口。"""
    return render_template('index.html')

@app.route('/osm')
def osm():
    """保留的旧版页面入口。"""
    return render_template('templates/osm.html')

# ===== 基于 JSON 的评测页面 =====
def load_all_cases():
    """读取所有案例 JSON 数据。"""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/evaluation')
def evaluation():
    """服务端抽样渲染评测页面。
    - 参数：n=数量(默认15)、seed=随机种子（复现实验）。
    """
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

# ===== 简化版页面（前端从 cases.json 抽样） =====
@app.route('/osm_simple')
def osm_simple():
    """前端自取 cases.json 并随机展示若干案例的简单页面。"""
    return render_template('templates/osm_simple.html')

@app.route('/thank_you')
def thank_you():
    """提交成功后的感谢页面。"""
    return render_template('templates/thank_you.html')

# ===== 静态资源路由（供前端直接访问） =====
@app.route('/data/<path:filename>')
def serve_data(filename):
    """提供 data/ 目录下的静态 JSON 文件。"""
    return send_from_directory(BASE_DIR / 'data', filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    """提供 images/ 目录下的静态图片（手工整理的图）。"""
    return send_from_directory(BASE_DIR / 'images', filename)

@app.route('/img/<path:filename>')
def serve_img(filename):
    """提供 img/ 目录下的图片（自动脚本生成或分组目录）。"""
    return send_from_directory(BASE_DIR / 'img', filename)

@app.route('/maps/<path:filename>')
def serve_maps(filename):
    """提供 maps/ 下的地图页面（含 hk_**** 等分组子目录）。"""
    return send_from_directory(BASE_DIR / 'maps', filename)

@app.route('/annotated_maps/<path:filename>')
def serve_annotated_maps(filename):
    """提供 annotated_maps/ 下的标注版地图页面。"""
    return send_from_directory(BASE_DIR / 'annotated_maps', filename)

@app.route('/healthz')
def healthz():
    """健康检查：用于 Render 等平台在冷启动时探活。"""
    return jsonify({
        'status': 'ok',
        'db_url_set': bool(DATABASE_URL),
    })

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        # 数据库短暂不可用时不要让进程退出，Render 会重试健康检查
        print(f"[WARN] init_db failed: {e}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
    # PORT=9000 python3 app.py                                            
    # http://127.0.0.1:9000/osm_simple
    # http://127.0.0.1:9000