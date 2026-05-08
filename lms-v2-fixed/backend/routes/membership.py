"""Membership routes"""
import jwt, datetime
from flask import Blueprint, request, jsonify
from db import query

membership_bp = Blueprint('membership', __name__)
SECRET = 'lms-library-secret-2024'
PLANS  = {'basic':90,'standard':180,'premium':365}
PRICES = {'basic':199,'standard':399,'premium':699}

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@membership_bp.route('/my', methods=['GET'])
def my_membership():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    r = query("SELECT * FROM membership_cards WHERE user_id=%s", (p['user_id'],), fetchone=True)
    return jsonify(r or {})

@membership_bp.route('/apply', methods=['POST'])
def apply():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    d    = request.get_json()
    plan = d.get('plan','basic')
    amt  = PRICES.get(plan, 199)
    txn  = d.get('txn_id','')
    # Check if already applied
    existing = query("SELECT id,status FROM membership_cards WHERE user_id=%s",
                     (p['user_id'],), fetchone=True)
    if existing and existing['status'] == 'approved':
        return jsonify({'error':'Already have an active membership'}), 400
    if existing:
        query("""UPDATE membership_cards SET plan=%s,amount=%s,txn_id=%s,
                 payment_date=NOW(),status='pending' WHERE user_id=%s""",
              (plan, amt, txn, p['user_id']))
    else:
        query("""INSERT INTO membership_cards (user_id,plan,amount,txn_id,payment_date,status)
                 VALUES (%s,%s,%s,%s,NOW(),'pending')""",
              (p['user_id'], plan, amt, txn))
    query("""INSERT INTO payments (user_id,issued_id,amount,method,txn_id)
             VALUES (%s,NULL,%s,'upi',%s)""",
          (p['user_id'], amt, txn or None))
    # Notify admin
    user = query("SELECT name FROM users WHERE id=%s", (p['user_id'],), fetchone=True)
    query("""INSERT INTO notifications (user_id,title,message,type)
             SELECT id,%s,%s,'info' FROM users WHERE role='admin'""",
          (f"Membership Request: {user['name']}",
           f"{user['name']} applied for {plan} plan (Rs.{amt}). Please review and approve."))
    return jsonify({'message':'Application submitted. Waiting for admin approval.'}), 201

@membership_bp.route('/all', methods=['GET'])
def all_memberships():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT m.*,u.name,u.email,u.member_id,u.phone
                    FROM membership_cards m JOIN users u ON m.user_id=u.id
                    ORDER BY m.payment_date DESC""", fetch=True)
    return jsonify(rows)

@membership_bp.route('/approve/<int:uid>', methods=['POST'])
def approve(uid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    mc = query("SELECT * FROM membership_cards WHERE user_id=%s", (uid,), fetchone=True)
    if not mc: return jsonify({'error':'Not found'}), 404
    today    = datetime.date.today()
    end_date = today + datetime.timedelta(days=PLANS.get(mc['plan'],90))
    query("""UPDATE membership_cards
             SET status='approved',approved_at=NOW(),start_date=%s,end_date=%s
             WHERE user_id=%s""", (today, end_date, uid))
    query("""INSERT INTO notifications (user_id,title,message,type)
             VALUES (%s,'Membership Approved',
             %s,'success')""",
          (uid, f"Your {mc['plan']} membership is approved! Valid till {end_date}. Your card is ready."))
    return jsonify({'message':'Membership approved'})

@membership_bp.route('/reject/<int:uid>', methods=['POST'])
def reject(uid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    query("UPDATE membership_cards SET status='rejected' WHERE user_id=%s", (uid,))
    d = request.get_json() or {}
    query("""INSERT INTO notifications (user_id,title,message,type)
             VALUES (%s,'Membership Rejected',%s,'warning')""",
          (uid, d.get('reason','Your membership application was rejected. Please contact the library.')))
    return jsonify({'message':'Membership rejected'})
