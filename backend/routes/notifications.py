"""Notifications routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

notifications_bp = Blueprint('notifications', __name__)
SECRET = 'lms-library-secret-2024'

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@notifications_bp.route('/', methods=['GET'])
def get_notifs():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT * FROM notifications
                    WHERE user_id=%s OR user_id IS NULL
                    ORDER BY created_at DESC LIMIT 50""",
                 (p['user_id'],), fetch=True)
    return jsonify(rows)

@notifications_bp.route('/unread-count', methods=['GET'])
def unread_count():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    r = query("""SELECT COUNT(*) as count FROM notifications
                 WHERE (user_id=%s OR user_id IS NULL) AND is_read=0""",
              (p['user_id'],), fetchone=True)
    return jsonify(r)

@notifications_bp.route('/send', methods=['POST'])
def send_notif():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json()
    user_id = d.get('user_id')  # None = broadcast to all
    query("""INSERT INTO notifications (user_id,title,message,type)
             VALUES (%s,%s,%s,%s)""",
          (user_id, d['title'], d.get('message',''), d.get('type','info')))
    return jsonify({'message':'Notification sent'}), 201

@notifications_bp.route('/read/<int:nid>', methods=['PUT'])
def mark_read(nid):
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    query("UPDATE notifications SET is_read=1 WHERE id=%s", (nid,))
    return jsonify({'message':'Marked as read'})

@notifications_bp.route('/read-all', methods=['PUT'])
def mark_all_read():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    query("UPDATE notifications SET is_read=1 WHERE user_id=%s OR user_id IS NULL",
          (p['user_id'],))
    return jsonify({'message':'All marked as read'})
