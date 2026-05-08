"""Library Visitors routes — who is currently in the library"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

visitors_bp = Blueprint('visitors', __name__)
SECRET = 'lms-library-secret-2024'

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@visitors_bp.route('/current', methods=['GET'])
def current():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT v.*,u.name,u.member_id,u.phone
                    FROM library_visitors v JOIN users u ON v.user_id=u.id
                    WHERE v.status='in' ORDER BY v.check_in DESC""", fetch=True)
    return jsonify(rows)

@visitors_bp.route('/checkin', methods=['POST'])
def checkin():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json(silent=True) or {}
    uid = d.get('user_id') if p['role'] == 'admin' else p['user_id']
    if not uid:
        return jsonify({'error':'User is required'}), 400
    # Check if already in
    existing = query("SELECT id FROM library_visitors WHERE user_id=%s AND status='in'",
                     (uid,), fetchone=True)
    if existing: return jsonify({'error':'Already checked in'}), 400
    query("INSERT INTO library_visitors (user_id,status) VALUES (%s,'in')", (uid,))
    return jsonify({'message':'Checked in'}), 201

@visitors_bp.route('/checkout/<int:uid>', methods=['POST'])
def checkout(uid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    query("""UPDATE library_visitors SET status='out',check_out=NOW()
             WHERE user_id=%s AND status='in'""", (uid,))
    return jsonify({'message':'Checked out'})

@visitors_bp.route('/checkout', methods=['POST'])
def checkout_self():
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error':'Unauthorized'}), 401
    query("""UPDATE library_visitors SET status='out',check_out=NOW()
             WHERE user_id=%s AND status='in'""", (p['user_id'],))
    return jsonify({'message':'Checked out'})

@visitors_bp.route('/my-status', methods=['GET'])
def my_status():
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error':'Unauthorized'}), 401
    row = query("""SELECT status,check_in,check_out
                   FROM library_visitors
                   WHERE user_id=%s
                   ORDER BY check_in DESC
                   LIMIT 1""", (p['user_id'],), fetchone=True)
    current = query("""SELECT id,check_in FROM library_visitors
                       WHERE user_id=%s AND status='in'
                       ORDER BY check_in DESC
                       LIMIT 1""", (p['user_id'],), fetchone=True)
    return jsonify({
        'is_in': bool(current),
        'current_check_in': current['check_in'] if current else None,
        'last_record': row
    })

@visitors_bp.route('/history', methods=['GET'])
def history():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT v.*,u.name,u.member_id
                    FROM library_visitors v JOIN users u ON v.user_id=u.id
                    ORDER BY v.check_in DESC LIMIT 100""", fetch=True)
    return jsonify(rows)
