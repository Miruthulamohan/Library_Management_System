"""Dashboard routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

dashboard_bp = Blueprint('dashboard', __name__)
SECRET = 'lms-library-secret-2024'

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@dashboard_bp.route('/admin-stats', methods=['GET'])
def admin_stats():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    books    = query("SELECT COUNT(*) as total, SUM(available) as available FROM books", fetchone=True)
    students = query("SELECT COUNT(*) as total FROM users WHERE role='student'", fetchone=True)
    issued   = query("SELECT COUNT(*) as total FROM issued_books WHERE status='issued'", fetchone=True)
    overdue  = query("SELECT COUNT(*) as total FROM issued_books WHERE status='issued' AND due_date < CURDATE()", fetchone=True)
    fines    = query("SELECT SUM(amount) as total FROM payments", fetchone=True)
    members  = query("SELECT COUNT(*) as total FROM membership_cards WHERE status='approved'", fetchone=True)
    pending  = query("SELECT COUNT(*) as total FROM membership_cards WHERE status='pending'", fetchone=True)
    visitors = query("SELECT COUNT(*) as total FROM library_visitors WHERE status='in'", fetchone=True)
    return jsonify({
        'total_books'    : books['total'] or 0,
        'available_books': books['available'] or 0,
        'total_students' : students['total'] or 0,
        'issued_books'   : issued['total'] or 0,
        'overdue_books'  : overdue['total'] or 0,
        'total_fines'    : float(fines['total'] or 0),
        'active_members' : members['total'] or 0,
        'pending_approvals': pending['total'] or 0,
        'visitors_now'   : visitors['total'] or 0,
    })

@dashboard_bp.route('/student-stats', methods=['GET'])
def student_stats():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    r = query("""SELECT
                   COUNT(*) as total_borrowed,
                   SUM(CASE WHEN status='issued' THEN 1 ELSE 0 END) as currently_issued,
                   SUM(CASE WHEN status='issued' AND due_date < CURDATE() THEN 1 ELSE 0 END) as overdue,
                   SUM(CASE WHEN fine_paid=0 AND fine>0 THEN fine ELSE 0 END) as pending_fine
                 FROM issued_books WHERE user_id=%s""",
              (p['user_id'],), fetchone=True)
    return jsonify(r)
