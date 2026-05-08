"""Auth routes"""
import jwt, bcrypt, datetime
from flask import Blueprint, request, jsonify
from db import query

auth_bp = Blueprint('auth', __name__)
SECRET  = 'lms-library-secret-2024'

def make_token(user_id, role):
    return jwt.encode({
        'user_id': user_id, 'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, SECRET, algorithm='HS256')

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@auth_bp.route('/login', methods=['POST'])
def login():
    d     = request.get_json()
    email = d.get('email','').strip().lower()
    pw    = d.get('password','')
    user  = query("SELECT * FROM users WHERE email=%s AND is_active=1", (email,), fetchone=True)
    if not user or not bcrypt.checkpw(pw.encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = make_token(user['id'], user['role'])
    return jsonify({'token': token, 'role': user['role'], 'name': user['name'],
                    'member_id': user['member_id'], 'user_id': user['id']})

@auth_bp.route('/register', methods=['POST'])
def register():
    d     = request.get_json()
    name  = d.get('name','').strip()
    email = d.get('email','').strip().lower()
    pw    = d.get('password','')
    phone = d.get('phone','')
    if not name or not email or not pw:
        return jsonify({'error': 'Name, email and password required'}), 400
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    try:
        count = query("SELECT COUNT(*) as c FROM users", fetchone=True)['c']
        member_id = f"STU{count+1:04d}"
        uid = query("""INSERT INTO users (name,email,password,phone,role,member_id)
                       VALUES (%s,%s,%s,%s,'student',%s)""",
                    (name, email, hashed, phone, member_id), lastrowid=True)
        token = make_token(uid, 'student')
        return jsonify({'token': token, 'role': 'student', 'name': name,
                        'member_id': member_id, 'user_id': uid}), 201
    except Exception as e:
        if 'Duplicate' in str(e): return jsonify({'error': 'Email already registered'}), 409
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
def profile():
    p = get_payload()
    if not p: return jsonify({'error': 'Unauthorized'}), 401
    user = query("SELECT id,name,email,phone,address,role,member_id,created_at FROM users WHERE id=%s",
                 (p['user_id'],), fetchone=True)
    return jsonify(user or {})

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    p = get_payload()
    if not p: return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json()
    query("UPDATE users SET name=%s,phone=%s,address=%s WHERE id=%s",
          (d.get('name'), d.get('phone'), d.get('address'), p['user_id']))
    return jsonify({'message': 'Profile updated'})

@auth_bp.route('/students', methods=['GET'])
def students():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error': 'Unauthorized'}), 401
    rows = query("""SELECT id,name,email,phone,member_id,created_at
                    FROM users WHERE role='student' ORDER BY created_at DESC""", fetch=True)
    return jsonify(rows)

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error': 'Unauthorized'}), 401
    d      = request.get_json()
    new_pw = d.get('password','')
    if len(new_pw) < 6: return jsonify({'error': 'Min 6 characters'}), 400
    hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    query("UPDATE users SET password=%s WHERE role='admin'", (hashed,))
    return jsonify({'message': 'Password updated'})
