"""Student Feedback Corner routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

feedback_bp = Blueprint('feedback', __name__)
SECRET = 'lms-library-secret-2024'


def get_payload():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None


# ── Student: submit feedback ──────────────────────────────────────────────
@feedback_bp.route('/submit', methods=['POST'])
def submit():
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json(silent=True) or {}
    subject  = (d.get('subject') or '').strip()
    message  = (d.get('message') or '').strip()
    category = d.get('category', 'general')
    rating   = d.get('rating')

    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400

    valid_cats = ('general', 'books', 'staff', 'facilities', 'suggestions')
    if category not in valid_cats:
        category = 'general'

    if rating is not None:
        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                rating = None
        except (ValueError, TypeError):
            rating = None

    query(
        """INSERT INTO student_feedback (user_id, category, subject, message, rating)
           VALUES (%s, %s, %s, %s, %s)""",
        (p['user_id'], category, subject, message, rating)
    )
    return jsonify({'message': 'Feedback submitted successfully'}), 201


# ── Student: view own feedback ────────────────────────────────────────────
@feedback_bp.route('/my', methods=['GET'])
def my_feedback():
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    rows = query(
        """SELECT f.id, f.category, f.subject, f.message, f.rating,
                  f.is_read, f.admin_reply, f.replied_at, f.created_at
           FROM student_feedback f
           WHERE f.user_id = %s
           ORDER BY f.created_at DESC""",
        (p['user_id'],), fetch=True
    )
    return jsonify(rows or [])


# ── Admin: list all feedback ──────────────────────────────────────────────
@feedback_bp.route('/admin/all', methods=['GET'])
def admin_all():
    p = get_payload()
    if not p or p['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    category = request.args.get('category', '')
    is_read  = request.args.get('is_read', '')

    sql = """SELECT f.id, f.category, f.subject, f.message, f.rating,
                    f.is_read, f.admin_reply, f.replied_at, f.created_at,
                    u.name AS student_name, u.member_id, u.email
             FROM student_feedback f
             JOIN users u ON f.user_id = u.id
             WHERE 1=1"""
    params = []

    if category:
        sql += ' AND f.category = %s'
        params.append(category)
    if is_read in ('0', '1'):
        sql += ' AND f.is_read = %s'
        params.append(int(is_read))

    sql += ' ORDER BY f.created_at DESC LIMIT 200'
    rows = query(sql, tuple(params) if params else None, fetch=True)
    return jsonify(rows or [])


# ── Admin: unread feedback count ──────────────────────────────────────────
@feedback_bp.route('/admin/unread-count', methods=['GET'])
def unread_count():
    p = get_payload()
    if not p or p['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    row = query(
        "SELECT COUNT(*) AS cnt FROM student_feedback WHERE is_read = 0",
        fetchone=True
    )
    return jsonify({'count': row['cnt'] if row else 0})


# ── Admin: mark as read + optional reply ─────────────────────────────────
@feedback_bp.route('/admin/<int:fid>', methods=['PUT'])
def admin_update(fid):
    p = get_payload()
    if not p or p['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json(silent=True) or {}
    reply = (d.get('admin_reply') or '').strip() or None

    if reply:
        query(
            """UPDATE student_feedback
               SET is_read=1, admin_reply=%s, replied_at=NOW()
               WHERE id=%s""",
            (reply, fid)
        )
    else:
        query("UPDATE student_feedback SET is_read=1 WHERE id=%s", (fid,))

    return jsonify({'message': 'Updated'})


# ── Admin: delete feedback ────────────────────────────────────────────────
@feedback_bp.route('/admin/<int:fid>', methods=['DELETE'])
def admin_delete(fid):
    p = get_payload()
    if not p or p['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    query("DELETE FROM student_feedback WHERE id=%s", (fid,))
    return jsonify({'message': 'Deleted'})
