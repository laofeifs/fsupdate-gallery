from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import json
import mimetypes

try:
    from PIL import Image
except Exception:
    Image = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS images (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               filename TEXT NOT NULL,
               original_name TEXT NOT NULL,
               file_size INTEGER,
               file_type TEXT,
               upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )'''
    )
    # 角色表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL, -- C/PF/PG/SG/SF
            gen INTEGER NOT NULL,   -- 1 ~ 9
            avatar_url TEXT,
            description TEXT,
            stats_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 职业排名（仅 C/PF/PG）
    cur.execute('''
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, -- C/PF/PG
            items_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 技巧
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL, -- PG/SG/SF/PF/C
            cover_url TEXT,
            summary TEXT,
            content_md TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 活动
    cur.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cover_url TEXT,
            time_range TEXT,
            body_md TEXT,
            link TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 代际图片映射表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS generation_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gen INTEGER NOT NULL,         -- 1 ~ 9
            filename TEXT NOT NULL,       -- 存储原图文件名 *_orig.ext
            url TEXT NOT NULL,            -- 对外访问URL（默认原图或512缩略图）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 战队信息表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gen INTEGER NOT NULL,         -- 1 ~ 9
            name TEXT NOT NULL,           -- 战队名称
            description TEXT,             -- 战队简介
            logo_url TEXT,                -- 战队logo
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 调查问卷表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT,               -- 玩家ID（可选）
            rankings_json TEXT NOT NULL,  -- 排名数据JSON
            feedback TEXT,                -- 留言反馈
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit(); conn.close()

def seed_data():
    """预置 1~9 代各若干角色、基础排名示例，仅在空库时执行"""
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    # 检查是否已有角色
    cur.execute('SELECT COUNT(*) FROM characters'); n = cur.fetchone()[0]
    if n == 0:
        sample_positions = ['PG', 'SG', 'SF', 'PF', 'C']
        for gen in range(1, 10):
            for i in range(1, 4):
                name = f'示例{gen}-{i}'
                pos = sample_positions[(gen + i) % 5]
                avatar_url = ''
                description = f'{name} 的介绍：这是第 {gen} 代的示例角色，位置 {pos}。'
                stats = {'shoot': 80, 'pass': 75, 'defense': 70, 'speed': 78}
                cur.execute('INSERT INTO characters (name, position, gen, avatar_url, description, stats_json) VALUES (?,?,?,?,?,?)',
                            (name, pos, gen, avatar_url, description, json.dumps(stats, ensure_ascii=False)))
        conn.commit()
    # 排名示例
    cur.execute('SELECT COUNT(*) FROM rankings'); rn = cur.fetchone()[0]
    if rn == 0:
        for cat in ('C','PF','PG'):
            items = [{'name': f'{cat}顶尖{idx}', 'score': 95-idx} for idx in range(5)]
            cur.execute('INSERT INTO rankings (category, items_json) VALUES (?, ?)', (cat, json.dumps(items, ensure_ascii=False)))
        conn.commit()
    # 技巧与活动示例（可选）
    cur.execute('SELECT COUNT(*) FROM tips'); tn = cur.fetchone()[0]
    if tn == 0:
        cur.execute('INSERT INTO tips (title, category, summary, content_md) VALUES (?,?,?,?)',
                    ('投篮基础', 'PG', '稳固出手姿势', '保持肘部内收，目视篮筐'))
        cur.execute('INSERT INTO tips (title, category, summary, content_md) VALUES (?,?,?,?)',
                    ('低位脚步', 'C', '背身单打要点', '重心低、卡位稳、第一步果断'))
        conn.commit()
    cur.execute('SELECT COUNT(*) FROM events'); en = cur.fetchone()[0]
    if en == 0:
        cur.execute('INSERT INTO events (title, time_range, body_md, link) VALUES (?,?,?,?)',
                    ('秋季杯报名开启', '2025-09-01 ~ 2025-10-01', '线上赛程，详情见官网', 'https://example.com'))
        conn.commit()
    
    # 战队示例数据
    cur.execute('SELECT COUNT(*) FROM teams'); tn = cur.fetchone()[0]
    if tn == 0:
        team_data = [
            (1, '雷霆战队', '第一代超特精英战队，以闪电般的速度和精准的投篮著称。'),
            (2, '风暴战队', '第二代超特战队，擅长团队配合和防守反击。'),
            (3, '烈焰战队', '第三代超特战队，以强大的进攻火力和激情四射的比赛风格闻名。'),
            (4, '冰霜战队', '第四代超特战队，冷静的战术执行和稳定的发挥是他们的标志。'),
            (5, '星辰战队', '第五代超特战队，如星辰般闪耀，技术全面且富有创造力。'),
            (6, '龙魂战队', '第六代超特战队，传承龙族精神，坚韧不拔的意志力。'),
            (7, '幻影战队', '第七代超特战队，如幻影般难以捉摸，战术变化多端。'),
            (8, '天启战队', '第八代超特战队，开启新时代的篮球理念，创新打法引领潮流。'),
            (9, '永恒战队', '第九代超特战队，追求永恒的篮球艺术，技术与艺术的完美结合。')
        ]
        for gen, name, description in team_data:
            cur.execute('INSERT INTO teams (gen, name, description) VALUES (?, ?, ?)', (gen, name, description))
        conn.commit()
    conn.close()


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def infer_extension(file_storage) -> str:
    """根据文件名或 MIME 类型推断扩展名，规避 Safari/特殊文件名问题"""
    try:
        name = file_storage.filename or ''
        ext = os.path.splitext(name)[1].lower().lstrip('.')
        if ext == 'jpeg':
            ext = 'jpg'
        if ext in ALLOWED_EXT:
            return ext
        # 尝试从 mimetype 推断
        mime = getattr(file_storage, 'mimetype', '') or getattr(file_storage, 'content_type', '')
        mapping = {
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/png': 'png',
            'image/webp': 'webp',
            'image/heic': 'jpg',  # 转存为jpg
        }
        ext2 = mapping.get(mime)
        if ext2 in ALLOWED_EXT:
            return ext2
    except Exception:
        pass
    return ''


@app.route('/api/images')
def api_images():
    try:
        page = max(int(request.args.get('page', '1')), 1)
        page_size = max(min(int(request.args.get('page_size', '30')), 100), 1)
    except ValueError:
        page, page_size = 1, 30
    offset = (page - 1) * page_size

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM images')
    total = cur.fetchone()[0]
    cur.execute('SELECT id, filename, original_name, file_size, file_type, upload_time FROM images ORDER BY upload_time DESC LIMIT ? OFFSET ?',
                (page_size, offset))
    rows = cur.fetchall()
    conn.close()

    items = []
    for rid, filename, original_name, file_size, file_type, upload_time in rows:
        base = filename.split('_orig.')[0] if '_orig.' in filename else None
        items.append({
            'id': rid,
            'filename': filename,
            'original_name': original_name,
            'file_size': file_size,
            'file_type': file_type,
            'upload_time': upload_time,
            'url': f'/uploads/{filename}',
            'thumb_128': f'/uploads/{base}_128.jpg' if base else f'/uploads/{filename}',
            'thumb_256': f'/uploads/{base}_256.jpg' if base else f'/uploads/{filename}',
            'thumb_512': f'/uploads/{base}_512.jpg' if base else f'/uploads/{filename}',
        })

    return jsonify({'total': total, 'page': page, 'page_size': page_size, 'items': items})


@app.route('/api/upload-image', methods=['POST'])
def api_upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    if not allowed_file(f.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    filename = secure_filename(f.filename)
    uid = uuid.uuid4().hex
    ext = filename.rsplit('.', 1)[1].lower()
    orig_name = f'{uid}_orig.{ext}'
    path_orig = os.path.join(UPLOAD_FOLDER, orig_name)
    f.save(path_orig)

    urls = {'original': f'/uploads/{orig_name}'}

    if Image is not None:
        try:
            with Image.open(path_orig) as im:
                im = im.convert('RGB')
                for size in [128, 256, 512]:
                    t = im.copy()
                    t.thumbnail((size, size))
                    name = f'{uid}_{size}.jpg'
                    t.save(os.path.join(UPLOAD_FOLDER, name), format='JPEG', quality=85)
                    urls[str(size)] = f'/uploads/{name}'
        except Exception as e:
            pass

    # 记录数据库
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO images (filename, original_name, file_size, file_type) VALUES (?, ?, ?, ?)',
                (orig_name, filename, os.path.getsize(path_orig), f.content_type))
    conn.commit(); conn.close()

    return jsonify({'success': True, 'urls': urls})


@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def api_delete_image(image_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT filename FROM images WHERE id=?', (image_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': '未找到图片'}), 404
    filename = row[0]
    cur.execute('DELETE FROM images WHERE id=?', (image_id,))
    conn.commit(); conn.close()
    try:
        p = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(p):
            os.remove(p)
        base = filename.split('_orig.')[0]
        for s in [128, 256, 512]:
            t = os.path.join(UPLOAD_FOLDER, f'{base}_{s}.jpg')
            if os.path.exists(t):
                os.remove(t)
    except Exception:
        pass
    return jsonify({'success': True})

@app.route('/api/generation-images', methods=['GET'])
def list_generation_images():
    gen = request.args.get('gen')
    params = []
    base = 'SELECT id, gen, filename, url, created_at FROM generation_images'
    if gen:
        # 支持小数代际参数
        try:
            gen_num = float(gen)
            base += ' WHERE gen=?'; params.append(gen_num)
        except ValueError:
            # 如果无法转换为数字，返回空列表
            return jsonify([])
    base += ' ORDER BY created_at DESC'
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute(base, params)
    rows = cur.fetchall(); conn.close()
    items = [{ 'id': r[0], 'gen': r[1], 'filename': r[2], 'url': r[3], 'created_at': r[4] } for r in rows]
    return jsonify(items)

@app.route('/api/upload-generation-image', methods=['POST'])
def upload_generation_image():
    gen = request.form.get('gen') or request.args.get('gen')
    if not gen:
        return jsonify({'success': False, 'error': '缺少 gen 参数'}), 400
    try:
        gen = float(gen)
        # 支持小数代际：1, 2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9
        valid_gens = [1, 2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9]
        if gen not in valid_gens:
            raise ValueError
    except Exception:
        return jsonify({'success': False, 'error': 'gen 必须是有效的代际值：1, 2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    if not allowed_file(f.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    # 保存文件（与 /api/upload-image 相同规则）
    filename = secure_filename(f.filename)
    uid = uuid.uuid4().hex
    ext = filename.rsplit('.', 1)[1].lower()
    orig_name = f'{uid}_orig.{ext}'
    path_orig = os.path.join(UPLOAD_FOLDER, orig_name)
    f.save(path_orig)

    # 缩略图
    display_url = f'/uploads/{orig_name}'
    if Image is not None:
        try:
            with Image.open(path_orig) as im:
                im = im.convert('RGB')
                for size in [128, 256, 512]:
                    t = im.copy(); t.thumbnail((size, size))
                    name = f'{uid}_{size}.jpg'
                    t.save(os.path.join(UPLOAD_FOLDER, name), format='JPEG', quality=85)
                    if size == 512:
                        display_url = f'/uploads/{name}'
        except Exception:
            pass

    # 记录 images 与 generation_images
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO images (filename, original_name, file_size, file_type) VALUES (?,?,?,?)',
                (orig_name, filename, os.path.getsize(path_orig), f.content_type))
    cur.execute('INSERT INTO generation_images (gen, filename, url) VALUES (?,?,?)', (gen, orig_name, display_url))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'url': display_url})

@app.route('/api/generation-images/<int:gid>', methods=['DELETE'])
def delete_generation_image(gid: int):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('SELECT filename FROM generation_images WHERE id=?', (gid,))
    row = cur.fetchone()
    if not row:
        conn.close(); return jsonify({'success': False, 'error': '未找到记录'}), 404
    filename = row[0]
    cur.execute('DELETE FROM generation_images WHERE id=?', (gid,))
    conn.commit(); conn.close()
    # 删除物理文件（原图+缩略图）
    try:
        p = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(p): os.remove(p)
        base = filename.split('_orig.')[0]
        for s in [128,256,512]:
            t = os.path.join(UPLOAD_FOLDER, f'{base}_{s}.jpg')
            if os.path.exists(t): os.remove(t)
    except Exception:
        pass
    return jsonify({'success': True})

@app.route('/api/upload-character-avatar', methods=['POST'])
def upload_character_avatar():
    """上传图片并直接绑定到角色的 avatar_url 字段，最简流程。
    表单字段：cid（或 character_id），file
    返回：{ success: true, url }
    """
    try:
        cid = request.form.get('cid') or request.form.get('character_id')
        if not cid:
            return jsonify({'success': False, 'error': '缺少角色ID（cid）'}), 400
        try:
            cid = int(cid)
        except Exception:
            return jsonify({'success': False, 'error': 'cid 非法'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有文件'}), 400
        f = request.files['file']
        if f.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'}), 400
            
        # 检查文件大小（限制为5MB）
        f.seek(0, 2)  # 移动到文件末尾
        file_size = f.tell()  # 获取文件大小
        f.seek(0)  # 重置到文件开头
        
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({'success': False, 'error': '文件太大，请选择小于5MB的图片'}), 400
            
        ext = infer_extension(f)
        if not ext:
            return jsonify({'success': False, 'error': '不支持的文件类型（请使用 PNG/JPG/WebP）'}), 400

        # 保存文件并生成缩略图
        filename = secure_filename(f.filename or f'upload.{ext}')
        uid = uuid.uuid4().hex
        orig_name = f'{uid}_orig.{ext}'
        path_orig = os.path.join(UPLOAD_FOLDER, orig_name)
        f.save(path_orig)

        display_url = f'/uploads/{orig_name}'
        if Image is not None:
            try:
                with Image.open(path_orig) as im:
                    # 限制图片尺寸，避免处理过大的图片
                    max_size = 2048
                    if im.size[0] > max_size or im.size[1] > max_size:
                        im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    
                    im = im.convert('RGB')
                    for size in [128, 256, 512]:
                        t = im.copy()
                        t.thumbnail((size, size), Image.Resampling.LANCZOS)
                        name = f'{uid}_{size}.jpg'
                        t.save(os.path.join(UPLOAD_FOLDER, name), format='JPEG', quality=88, optimize=True)
                        if size == 512:
                            display_url = f'/uploads/{name}'
            except Exception as e:
                print('Thumb error:', e)
                # 如果缩略图生成失败，使用原图
                display_url = f'/uploads/{orig_name}'

        # 记录 images 并更新角色 avatar_url
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute('INSERT INTO images (filename, original_name, file_size, file_type) VALUES (?,?,?,?)',
                    (orig_name, filename, os.path.getsize(path_orig), f.content_type))
        cur.execute('UPDATE characters SET avatar_url=? WHERE id=?', (display_url, cid))
        conn.commit(); conn.close()
        return jsonify({'success': True, 'url': display_url})
    except Exception as e:
        # 返回明确错误，便于前端提示
        print('Upload avatar error:', e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/cms')
def cms_page():
    return render_template('admin_console.html')

@app.route('/tier')
def tier_management():
    return render_template('tier_management.html')

@app.route('/upload-avatar')
def upload_avatar_page():
    return render_template('upload_avatar.html')

# ----------------- 角色 CRUD -----------------
@app.route('/api/characters', methods=['GET'])
def list_characters():
    gen = request.args.get('gen')
    position = request.args.get('position')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    base = 'SELECT id,name,position,gen,avatar_url,description,stats_json,created_at FROM characters'
    cond, params = [], []
    if gen:
        # 处理 gen1, gen2, gen3.5 这样的格式，提取数字部分
        if isinstance(gen, str) and gen.startswith('gen'):
            gen_num = gen[3:]  # 去掉 'gen' 前缀
        else:
            gen_num = gen
        # 支持小数代际（如3.5）
        try:
            gen_num = float(gen_num)
            cond.append('gen=?'); params.append(gen_num)
        except ValueError:
            # 如果无法转换为数字，忽略这个条件
            pass
    if position:
        cond.append('position=?'); params.append(position)
    if cond:
        base += ' WHERE ' + ' AND '.join(cond)
    base += ' ORDER BY gen ASC, id DESC'
    cur.execute(base, params)
    rows = cur.fetchall(); conn.close()
    items = []
    for r in rows:
        items.append({
            'id': r[0], 'name': r[1], 'position': r[2], 'gen': r[3],
            'avatar_url': r[4], 'description': r[5], 'stats_json': r[6], 'created_at': r[7]
        })
    return jsonify(items)

@app.route('/api/characters', methods=['POST'])
def create_character():
    data = request.json or {}
    name = data.get('name'); gen = data.get('gen')
    if not (name and gen):
        return jsonify({'success': False, 'error': '缺少必要字段：name 或 gen'}), 400
    position = data.get('position', 'C')  # 默认位置为C
    avatar_url = data.get('avatar_url'); description = data.get('description', '')
    stats_json = data.get('stats_json')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO characters (name, position, gen, avatar_url, description, stats_json) VALUES (?,?,?,?,?,?)',
                (name, position, float(gen), avatar_url, description, stats_json))
    conn.commit(); cid = cur.lastrowid; conn.close()
    return jsonify({'success': True, 'id': cid})

@app.route('/api/characters/<int:cid>', methods=['GET'])
def get_character(cid: int):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('SELECT id,name,position,gen,avatar_url,description,stats_json,created_at FROM characters WHERE id=?', (cid,))
    r = cur.fetchone(); conn.close()
    if not r:
        return jsonify({'success': False, 'error': '未找到角色'}), 404
    return jsonify({'id': r[0], 'name': r[1], 'position': r[2], 'gen': r[3], 'avatar_url': r[4], 'description': r[5], 'stats_json': r[6], 'created_at': r[7]})

@app.route('/api/characters/<int:cid>', methods=['PUT'])
def update_character(cid: int):
    try:
        data = request.json or {}
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        fields = ['name','gen','avatar_url','description','stats_json']
        sets, params = [], []
        for f in fields:
            if f in data:
                sets.append(f"{f}=?"); params.append(data[f])
        if not sets:
            return jsonify({'success': False, 'error': '无更新字段'}), 400
        params.append(cid)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('UPDATE characters SET ' + ','.join(sets) + ' WHERE id=?', params)
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/characters/<int:cid>', methods=['DELETE'])
def delete_character(cid: int):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('DELETE FROM characters WHERE id=?', (cid,))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ----------------- 职业排名（C/PF/PG） -----------------
@app.route('/api/rankings', methods=['GET'])
def get_ranking():
    category = request.args.get('category')
    if category not in ('C','PF','PG','ALL'):
        return jsonify({'success': False, 'error': 'category 必须是 C/PF/PG/ALL'}), 400
    
    # 如果是全职业，返回所有角色的天梯数据
    if category == 'ALL':
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 获取所有角色
        cur.execute('''
            SELECT id, name, avatar_url, position, gen 
            FROM characters 
            ORDER BY gen ASC, name ASC
        ''')
        characters = cur.fetchall()
        conn.close()
        
        # 为每个角色分配评分（基于代际和角色强度）
        tier_data = []
        for char in characters:
            char_id, name, avatar_url, position, gen = char
            
            # 基于代际分配基础分数
            base_score = 85 - (gen - 1) * 5  # 1代85分，2代80分，以此类推
            
            # 为不同角色添加微调分数（全职业通用）
            score_adjustments = {
                '示例1-3': 0,   # 1代示例
                '沃顿': 8,      # 2代强力
                '示例2-2': 0,   # 2代示例
                '麒麟': 9,      # 3代强力
                '酒鬼': 5,      # 3代强力
                '露美': 6,      # 4代强力
                '玛丽': 4,      # 4代
                '风雷': 9,      # 6代强力
                '钢铁剧毒': 5,  # 6代
                '雪舞': 1,      # 7代
                '月神': 7,      # 8代强力
                '亚克': 8,      # 9代强力
            }
            
            # 计算最终分数
            final_score = base_score + score_adjustments.get(name, 0)
            final_score = max(60, min(100, final_score))  # 限制在60-100分之间
            
            tier_data.append({
                'id': char_id,
                'name': name,
                'avatar_url': avatar_url,
                'position': position,
                'gen': gen,
                'score': final_score
            })
        
        # 按分数排序
        tier_data.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify(tier_data)
    
    # 如果是C职业，返回角色天梯数据
    if category == 'C':
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 获取所有C职业的角色
        cur.execute('''
            SELECT id, name, avatar_url, position, gen 
            FROM characters 
            WHERE position = 'C' 
            ORDER BY gen ASC, name ASC
        ''')
        characters = cur.fetchall()
        conn.close()
        
        # 为每个角色分配评分（基于代际和角色强度）
        tier_data = []
        for char in characters:
            char_id, name, avatar_url, position, gen = char
            
            # 基于代际分配基础分数
            base_score = 85 - (gen - 1) * 5  # 1代85分，2代80分，以此类推
            
            # 为不同角色添加微调分数
            score_adjustments = {
                '示例1-3': 0,   # 1代示例
                '沃顿': 8,      # 2代强力C
                '示例2-2': 0,   # 2代示例
                '麒麟': 9,      # 3代强力C
                '酒鬼': 5,      # 3代强力C
                '露美': 6,      # 4代强力C
                '玛丽': 4,      # 4代
                '风雷': 9,      # 6代强力C
                '钢铁剧毒': 5,  # 6代
                '雪舞': 1,      # 7代
                '月神': 7,      # 8代强力C
                '亚克': 8,      # 9代强力C
            }
            
            # 计算最终分数
            final_score = base_score + score_adjustments.get(name, 0)
            final_score = max(60, min(100, final_score))  # 限制在60-100分之间
            
            tier_data.append({
                'id': char_id,
                'name': name,
                'avatar_url': avatar_url,
                'position': position,
                'gen': gen,
                'score': final_score
            })
        
        # 按分数排序
        tier_data.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify(tier_data)
    
    # 其他职业保持原有逻辑
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT items_json, updated_at FROM rankings WHERE category=? ORDER BY updated_at DESC LIMIT 1', (category,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'category': category, 'items': [], 'updated_at': None})
    return jsonify({'category': category, 'items': row[0], 'updated_at': row[1]})

@app.route('/api/rankings', methods=['PUT'])
def put_ranking():
    data = request.json or {}
    category = data.get('category'); items_json = data.get('items_json')
    if category not in ('C','PF','PG','ALL'):
        return jsonify({'success': False, 'error': 'category 必须是 C/PF/PG/ALL'}), 400
    if items_json is None:
        return jsonify({'success': False, 'error': '缺少 items_json'}), 400
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO rankings (category, items_json) VALUES (?, ?)', (category, items_json))
    conn.commit(); conn.close()
    return jsonify({'success': True})

# ----------------- 技巧/活动 -----------------
@app.route('/api/tips', methods=['GET'])
def list_tips():
    category = request.args.get('category')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    base = 'SELECT id,title,category,cover_url,summary,content_md,updated_at FROM tips'
    params = []
    if category:
        base += ' WHERE category=?'; params.append(category)
    base += ' ORDER BY updated_at DESC'
    cur.execute(base, params)
    rows = cur.fetchall(); conn.close()
    items = []
    for r in rows:
        items.append({ 'id': r[0], 'title': r[1], 'category': r[2], 'cover_url': r[3], 'summary': r[4], 'content_md': r[5], 'updated_at': r[6] })
    return jsonify(items)

@app.route('/api/tips', methods=['POST'])
def create_tip():
    data = request.json or {}
    title = data.get('title'); category = data.get('category'); content_md = data.get('content_md','')
    if not (title and category):
        return jsonify({'success': False, 'error': '缺少必要字段'}), 400
    cover_url = data.get('cover_url'); summary = data.get('summary')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO tips (title, category, cover_url, summary, content_md) VALUES (?,?,?,?,?)',
                (title, category, cover_url, summary, content_md))
    conn.commit(); tid = cur.lastrowid; conn.close()
    return jsonify({'success': True, 'id': tid})

@app.route('/api/tips/<int:tid>', methods=['PUT','DELETE'])
def modify_tip(tid: int):
    if request.method == 'DELETE':
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute('DELETE FROM tips WHERE id=?', (tid,))
        conn.commit(); conn.close(); return jsonify({'success': True})
    data = request.json or {}
    fields = ['title','category','cover_url','summary','content_md']
    sets, params = [], []
    for f in fields:
        if f in data:
            sets.append(f"{f}=?"); params.append(data[f])
    if not sets:
        return jsonify({'success': False, 'error': '无更新字段'}), 400
    params.append(tid)
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('UPDATE tips SET ' + ','.join(sets) + ', updated_at=CURRENT_TIMESTAMP WHERE id=?', params)
    conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/events', methods=['GET'])
def list_events():
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('SELECT id,title,cover_url,time_range,body_md,link,updated_at FROM events ORDER BY updated_at DESC')
    rows = cur.fetchall(); conn.close()
    items = []
    for r in rows:
        items.append({ 'id': r[0], 'title': r[1], 'cover_url': r[2], 'time_range': r[3], 'body_md': r[4], 'link': r[5], 'updated_at': r[6] })
    return jsonify(items)

@app.route('/api/events', methods=['POST'])
def create_event():
    data = request.json or {}
    title = data.get('title'); body_md = data.get('body_md','')
    if not title:
        return jsonify({'success': False, 'error': '缺少标题'}), 400
    cover_url = data.get('cover_url'); time_range = data.get('time_range'); link = data.get('link')
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('INSERT INTO events (title, cover_url, time_range, body_md, link) VALUES (?,?,?,?,?)',
                (title, cover_url, time_range, body_md, link))
    conn.commit(); eid = cur.lastrowid; conn.close()
    return jsonify({'success': True, 'id': eid})

@app.route('/api/events/<int:eid>', methods=['PUT','DELETE'])
def modify_event(eid: int):
    if request.method == 'DELETE':
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute('DELETE FROM events WHERE id=?', (eid,))
        conn.commit(); conn.close(); return jsonify({'success': True})
    data = request.json or {}
    fields = ['title','cover_url','time_range','body_md','link']
    sets, params = [], []
    for f in fields:
        if f in data:
            sets.append(f"{f}=?"); params.append(data[f])
    if not sets:
        return jsonify({'success': False, 'error': '无更新字段'}), 400
    params.append(eid)
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute('UPDATE events SET ' + ','.join(sets) + ', updated_at=CURRENT_TIMESTAMP WHERE id=?', params)
    conn.commit(); conn.close()
    return jsonify({'success': True})

# 战队相关API
@app.route('/api/teams', methods=['GET'])
def list_teams():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    gen = request.args.get('gen')
    if gen:
        if isinstance(gen, str) and gen.startswith('gen'):
            gen_num = gen[3:]
        else:
            gen_num = gen
        # 支持小数代际（如3.5）
        try:
            gen_num = float(gen_num)
            cur.execute('SELECT * FROM teams WHERE gen=? ORDER BY id', (gen_num,))
        except ValueError:
            # 如果无法转换为数字，返回空列表
            conn.close()
            return jsonify([])
    else:
        cur.execute('SELECT * FROM teams ORDER BY gen, id')
    
    teams = []
    for row in cur.fetchall():
        teams.append({
            'id': row[0],
            'gen': row[1],
            'name': row[2],
            'description': row[3],
            'logo_url': row[4],
            'created_at': row[5]
        })
    conn.close()
    return jsonify(teams)

@app.route('/api/teams', methods=['POST'])
def create_team():
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO teams (gen, name, description, logo_url)
        VALUES (?, ?, ?, ?)
    ''', (data.get('gen'), data.get('name'), data.get('description'), data.get('logo_url')))
    conn.commit()
    team_id = cur.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': team_id})

@app.route('/api/teams/<int:tid>', methods=['GET', 'PUT', 'DELETE'])
def modify_team(tid: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if request.method == 'GET':
        cur.execute('SELECT * FROM teams WHERE id=?', (tid,))
        row = cur.fetchone()
        if row:
            team = {
                'id': row[0],
                'gen': row[1],
                'name': row[2],
                'description': row[3],
                'logo_url': row[4],
                'created_at': row[5]
            }
            conn.close()
            return jsonify(team)
        else:
            conn.close()
            return jsonify({'error': '战队不存在'}), 404
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            if not data:
                conn.close()
                return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
            # 验证必需字段
            if not data.get('gen') or not data.get('name'):
                conn.close()
                return jsonify({'success': False, 'error': '缺少必需字段：gen 或 name'}), 400
            
            cur.execute('''
                UPDATE teams SET gen=?, name=?, description=?, logo_url=?
                WHERE id=?
            ''', (data.get('gen'), data.get('name'), data.get('description'), data.get('logo_url'), tid))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    elif request.method == 'DELETE':
        cur.execute('DELETE FROM teams WHERE id=?', (tid,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

# 调查问卷相关API
@app.route('/api/survey/submit', methods=['POST'])
def submit_survey():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        # 验证必需字段
        if not data.get('rankings'):
            return jsonify({'success': False, 'error': '缺少排名数据'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 获取客户端标识（优先使用浏览器指纹，其次使用IP）
        client_id = data.get('clientId', '')
        if not client_id:
            client_ip = request.remote_addr
            if request.headers.get('X-Forwarded-For'):
                client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            client_id = f"ip_{client_ip}"
        
        # 检查是否已经提交过
        cur.execute('SELECT COUNT(*) FROM surveys WHERE player_id = ?', (client_id,))
        existing_count = cur.fetchone()[0]
        
        if existing_count > 0:
            conn.close()
            return jsonify({'success': False, 'error': '您已经提交过调查，每人只能投票一轮'}), 403
        
        cur.execute('''
            INSERT INTO surveys (player_id, rankings_json, feedback)
            VALUES (?, ?, ?)
        ''', (
            client_id,
            json.dumps(data.get('rankings'), ensure_ascii=False),
            data.get('feedback', '')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '调查提交成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/survey/results', methods=['GET'])
def get_survey_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 获取所有调查结果
        cur.execute('''
            SELECT id, player_id, rankings_json, feedback, created_at 
            FROM surveys 
            ORDER BY created_at DESC
        ''')
        
        surveys = []
        for row in cur.fetchall():
            surveys.append({
                'id': row[0],
                'player_id': row[1],
                'rankings': json.loads(row[2]) if row[2] else {},
                'feedback': row[3],
                'created_at': row[4]
            })
        
        # 统计参与人数
        cur.execute('SELECT COUNT(*) FROM surveys')
        total_participants = cur.fetchone()[0]
        
        # 获取所有角色信息用于ID到名称的映射
        cur.execute('SELECT id, name, gen FROM characters')
        characters_map = {}
        for row in cur.fetchall():
            char_id, name, gen = row
            characters_map[char_id] = {'name': name, 'gen': gen}
        
        # 统计各职业的排名数据
        position_stats = {}
        for survey in surveys:
            for position, rankings in survey['rankings'].items():
                if position not in position_stats:
                    position_stats[position] = {}
                
                for i, char in enumerate(rankings):
                    char_id = char['id']
                    if char_id not in position_stats[position]:
                        # 从数据库获取真实的角色信息
                        char_info = characters_map.get(char_id, {'name': char.get('name', '未知角色'), 'gen': char.get('gen', 0)})
                        position_stats[position][char_id] = {
                            'name': char_info['name'],
                            'gen': char_info['gen'],
                            'total_votes': 0,
                            'total_score': 0,
                            'rankings': []
                        }
                    
                    position_stats[position][char_id]['total_votes'] += 1
                    position_stats[position][char_id]['total_score'] += (i + 1)  # 排名分数（第1名=1分，第2名=2分...）
                    position_stats[position][char_id]['rankings'].append(i + 1)
        
        # 计算平均排名
        for position in position_stats:
            for char_id in position_stats[position]:
                char_stats = position_stats[position][char_id]
                char_stats['avg_rank'] = char_stats['total_score'] / char_stats['total_votes']
                char_stats['avg_rank'] = round(char_stats['avg_rank'], 2)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_participants': total_participants,
            'surveys': surveys,
            'position_stats': position_stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/survey/stats', methods=['GET'])
def get_survey_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 总参与人数
        cur.execute('SELECT COUNT(*) FROM surveys')
        total_participants = cur.fetchone()[0]
        
        # 今日参与人数
        cur.execute('''
            SELECT COUNT(*) FROM surveys 
            WHERE DATE(created_at) = DATE('now')
        ''')
        today_participants = cur.fetchone()[0]
        
        # 各职业参与度
        cur.execute('''
            SELECT rankings_json FROM surveys
        ''')
        
        position_participation = {'C': 0, 'PF': 0, 'SF': 0, 'SG': 0, 'PG': 0, 'SW': 0}
        
        for row in cur.fetchall():
            rankings = json.loads(row[0]) if row[0] else {}
            for position in rankings:
                if position in position_participation and len(rankings[position]) > 0:
                    position_participation[position] += 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_participants': total_participants,
            'today_participants': today_participants,
            'position_participation': position_participation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/survey')
def survey_page():
    return render_template('survey_v2.html')

@app.route('/test-ranking')
def test_ranking():
    return render_template('test_ranking.html')

@app.route('/test-api')
def test_api():
    return render_template('test_api.html')

@app.route('/survey/results')
def survey_results_page():
    return render_template('survey_results.html')

@app.route('/api/survey/check-voted', methods=['POST'])
def check_voted():
    try:
        data = request.get_json()
        client_id = data.get('clientId', '')
        
        if not client_id:
            # 如果没有客户端ID，使用IP检查
            client_ip = request.remote_addr
            if request.headers.get('X-Forwarded-For'):
                client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            client_id = f"ip_{client_ip}"
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM surveys WHERE player_id = ?', (client_id,))
        existing_count = cur.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'hasVoted': existing_count > 0
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 静态文件服务
@app.route('/new_frontend/<path:filename>')
def serve_frontend(filename):
    frontend_dir = os.path.join(os.path.dirname(BASE_DIR), 'new_frontend')
    return send_from_directory(frontend_dir, filename)

def main():
    init_db()
    # 暂时跳过seed_data()以减少启动时间
    # seed_data()
    port = int(os.environ.get('PORT', '5101'))
    # 优化服务器配置，减少CPU使用率
    app.run(
        debug=False,  # 关闭调试模式，减少CPU使用
        host='0.0.0.0', 
        port=port,
        threaded=True,  # 启用多线程
        processes=1,    # 限制进程数
        use_reloader=False  # 禁用自动重载
    )


if __name__ == '__main__':
    main()


