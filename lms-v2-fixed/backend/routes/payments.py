"""Payments routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

payments_bp = Blueprint('payments', __name__)
SECRET = 'lms-library-secret-2024'

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@payments_bp.route('/', methods=['GET'])
def get_payments():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    if p['role'] == 'admin':
        rows = query("""SELECT p.*,u.name as student_name,u.member_id
                        FROM payments p JOIN users u ON p.user_id=u.id
                        ORDER BY p.paid_at DESC""", fetch=True)
    else:
        rows = query("SELECT * FROM payments WHERE user_id=%s ORDER BY paid_at DESC",
                     (p['user_id'],), fetch=True)
    return jsonify(rows)

@payments_bp.route('/pay', methods=['POST'])
def pay():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json()
    query("""INSERT INTO payments (user_id,issued_id,amount,method,txn_id)
             VALUES (%s,%s,%s,%s,%s)""",
          (p['user_id'],d.get('issued_id'),d.get('amount'),
           d.get('method','qr'),d.get('txn_id')))
    if d.get('issued_id'):
        query("UPDATE issued_books SET fine_paid=1 WHERE id=%s", (d['issued_id'],))
    return jsonify({'message':'Payment recorded'}), 201
