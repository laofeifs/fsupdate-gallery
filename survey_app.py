from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 调查表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            rankings_json TEXT NOT NULL,
            feedback TEXT,
            client_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 角色表（简化版）
    cur.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            gen INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/api/characters')
def get_characters():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, name, position, gen 
            FROM characters 
            WHERE gen >= 5 AND gen <= 9
            ORDER BY gen, name
        ''')
        
        characters = []
        for row in cur.fetchall():
            characters.append({
                'id': row[0],
                'name': row[1],
                'position': row[2],
                'gen': row[3]
            })
        
        conn.close()
        return jsonify(characters)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/survey/submit', methods=['POST'])
def submit_survey():
    try:
        data = request.get_json()
        player_id = data.get('playerId', '').strip()
        rankings = data.get('rankings', {})
        feedback = data.get('feedback', '').strip()
        client_id = data.get('clientId', '')
        
        if not player_id:
            return jsonify({'success': False, 'error': '玩家ID不能为空'}), 400
        
        # 检查是否已经投票
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM surveys WHERE player_id = ?', (player_id,))
        existing_count = cur.fetchone()[0]
        
        if existing_count > 0:
            conn.close()
            return jsonify({'success': False, 'error': '您已经参与过投票了'}), 400
        
        # 保存调查数据
        cur.execute('''
            INSERT INTO surveys (player_id, rankings_json, feedback, client_id)
            VALUES (?, ?, ?, ?)
        ''', (player_id, json.dumps(rankings), feedback, client_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/survey/check-voted', methods=['POST'])
def check_voted():
    try:
        data = request.get_json()
        client_id = data.get('clientId', '')
        
        if not client_id:
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

@app.route('/api/survey/stats')
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
        cur.execute('SELECT rankings_json FROM surveys')
        
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

@app.route('/api/survey/results')
def get_survey_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # 获取所有调查数据
        cur.execute('''
            SELECT id, player_id, rankings_json, feedback, created_at
            FROM surveys
            ORDER BY created_at DESC
        ''')
        
        surveys = []
        for row in cur.fetchall():
            survey_id, player_id, rankings_json, feedback, created_at = row
            rankings = json.loads(rankings_json) if rankings_json else {}
            
            surveys.append({
                'id': survey_id,
                'player_id': player_id,
                'rankings': rankings,
                'feedback': feedback,
                'created_at': created_at
            })
        
        # 计算排名统计
        position_stats = {'C': {}, 'PF': {}, 'SF': {}, 'SG': {}, 'PG': {}, 'SW': {}}
        
        for survey in surveys:
            for position, rankings in survey['rankings'].items():
                if position not in position_stats:
                    continue
                    
                for ranking in rankings:
                    char_id = ranking['id']
                    rank = ranking.get('rank', 1)
                    
                    if char_id not in position_stats[position]:
                        position_stats[position][char_id] = {
                            'name': ranking['name'],
                            'gen': ranking['gen'],
                            'rankings': [],
                            'total_score': 0,
                            'total_votes': 0
                        }
                    
                    position_stats[position][char_id]['rankings'].append(rank)
                    position_stats[position][char_id]['total_score'] += rank
                    position_stats[position][char_id]['total_votes'] += 1
        
        # 计算平均排名
        for position in position_stats:
            for char_id in position_stats[position]:
                char_data = position_stats[position][char_id]
                char_data['avg_rank'] = round(char_data['total_score'] / char_data['total_votes'], 1)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'surveys': surveys,
            'position_stats': position_stats,
            'total_participants': len(surveys)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/survey')
def survey_page():
    return render_template('survey_v2.html')

@app.route('/survey/results')
def survey_results_page():
    return render_template('survey_results.html')

if __name__ == '__main__':
    init_db()
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5101,
        threaded=True,
        use_reloader=False
    )
