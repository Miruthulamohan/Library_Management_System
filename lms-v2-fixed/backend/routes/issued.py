"""Issued books routes"""
import jwt, datetime
from flask import Blueprint, request, jsonify
from db import query

issued_bp = Blueprint('issued', __name__)
SECRET    = 'lms-library-secret-2024'
FINE_PER_DAY = 10.00

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@issued_bp.route('/', methods=['GET'])
def get_issued():
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    if p['role'] == 'admin':
        rows = query("""SELECT i.*,b.title,b.author,u.name as student_name,u.member_id
                        FROM issued_books i JOIN books b ON i.book_id=b.id
                        JOIN users u ON i.user_id=u.id ORDER BY i.issued_date DESC""", fetch=True)
    else:
        rows = query("""SELECT i.*,b.title,b.author,b.cover_url
                        FROM issued_books i JOIN books b ON i.book_id=b.id
                        WHERE i.user_id=%s ORDER BY i.issued_date DESC""",
                     (p['user_id'],), fetch=True)
    return jsonify(rows)

@issued_bp.route('/issue', methods=['POST'])
def issue_book():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json()
    book = query("SELECT available FROM books WHERE id=%s", (d['book_id'],), fetchone=True)
    if not book or book['available'] < 1: return jsonify({'error':'Book not available'}), 400
    today    = datetime.date.today()
    due_date = today + datetime.timedelta(days=int(d.get('days',14)))
    iid = query("""INSERT INTO issued_books (book_id,user_id,issued_date,due_date,status)
                   VALUES (%s,%s,%s,%s,'issued')""",
                (d['book_id'],d['user_id'],today,due_date), lastrowid=True)
    query("UPDATE books SET available=available-1 WHERE id=%s", (d['book_id'],))
    # Notify student
    student = query("SELECT name FROM users WHERE id=%s", (d['user_id'],), fetchone=True)
    book_info = query("SELECT title FROM books WHERE id=%s", (d['book_id'],), fetchone=True)
    query("""INSERT INTO notifications (user_id,title,message,type)
             VALUES (%s,%s,%s,'info')""",
          (d['user_id'], 'Book Issued',
           f"'{book_info['title']}' issued to you. Due date: {due_date}"))
    return jsonify({'message':'Book issued','due_date':str(due_date)}), 201

@issued_bp.route('/borrow', methods=['POST'])
def borrow_book():
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json() or {}
    book_id = d.get('book_id')
    if not book_id:
        return jsonify({'error':'Book is required'}), 400
    member = query("SELECT status FROM membership_cards WHERE user_id=%s", (p['user_id'],), fetchone=True)
    if not member or member['status'] != 'approved':
        return jsonify({'error':'Active membership is required to borrow books'}), 400
    active = query("""SELECT COUNT(*) as c FROM issued_books
                      WHERE user_id=%s AND status='issued'""", (p['user_id'],), fetchone=True)
    if (active['c'] or 0) >= 3:
        return jsonify({'error':'Borrow limit reached (max 3 active books)'}), 400
    book = query("SELECT available,title FROM books WHERE id=%s", (book_id,), fetchone=True)
    if not book or book['available'] < 1:
        return jsonify({'error':'Book not available'}), 400
    today = datetime.date.today()
    due_date = today + datetime.timedelta(days=14)
    query("""INSERT INTO issued_books (book_id,user_id,issued_date,due_date,status)
             VALUES (%s,%s,%s,%s,'issued')""", (book_id, p['user_id'], today, due_date))
    query("UPDATE books SET available=available-1 WHERE id=%s", (book_id,))
    return jsonify({'message':'Book borrowed successfully','due_date':str(due_date)}), 201

@issued_bp.route('/return/<int:iid>', methods=['POST'])
def return_book(iid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rec = query("SELECT * FROM issued_books WHERE id=%s", (iid,), fetchone=True)
    if not rec: return jsonify({'error':'Not found'}), 404
    if rec['status'] == 'returned': return jsonify({'error':'Already returned'}), 400
    return_date = datetime.date.today()
    delay_days  = max(0, (return_date - rec['due_date']).days) if rec['due_date'] else 0
    fine         = round(delay_days * FINE_PER_DAY, 2)
    query("UPDATE issued_books SET return_date=%s,fine=%s,status='returned' WHERE id=%s",
          (return_date, fine, iid))
    query("UPDATE books SET available=available+1 WHERE id=%s", (rec['book_id'],))
    if fine > 0:
        query("""INSERT INTO notifications (user_id,title,message,type)
                 VALUES (%s,%s,%s,'warning')""",
              (rec['user_id'], 'Fine Charged',
               f"Book returned with a fine of Rs.{fine:.2f}. Please pay at the library."))
    return jsonify({'message':'Book returned','fine':fine})

@issued_bp.route('/return-self/<int:iid>', methods=['POST'])
def return_book_self(iid):
    p = get_payload()
    if not p or p['role'] != 'student':
        return jsonify({'error':'Unauthorized'}), 401
    rec = query("SELECT * FROM issued_books WHERE id=%s AND user_id=%s", (iid, p['user_id']), fetchone=True)
    if not rec:
        return jsonify({'error':'Not found'}), 404
    if rec['status'] == 'returned':
        return jsonify({'error':'Already returned'}), 400
    return_date = datetime.date.today()
    delay_days  = max(0, (return_date - rec['due_date']).days) if rec['due_date'] else 0
    fine         = round(delay_days * FINE_PER_DAY, 2)
    query("UPDATE issued_books SET return_date=%s,fine=%s,status='returned' WHERE id=%s",
          (return_date, fine, iid))
    query("UPDATE books SET available=available+1 WHERE id=%s", (rec['book_id'],))
    if fine > 0:
        query("""INSERT INTO notifications (user_id,title,message,type)
                 VALUES (%s,%s,%s,'warning')""",
              (p['user_id'], 'Fine Charged',
               f"Book returned with a fine of Rs.{fine:.2f}. Please pay at the library."))
    return jsonify({'message':'Book returned','fine':fine})

@issued_bp.route('/overdue', methods=['GET'])
def overdue():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT i.*,b.title,u.name as student_name,u.member_id,u.email,u.phone,
                           DATEDIFF(CURDATE(),i.due_date) as overdue_days
                    FROM issued_books i JOIN books b ON i.book_id=b.id
                    JOIN users u ON i.user_id=u.id
                    WHERE i.status='issued' AND i.due_date < CURDATE()
                    ORDER BY overdue_days DESC""", fetch=True)
    return jsonify(rows)

@issued_bp.route('/who-has-books', methods=['GET'])
def who_has_books():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    rows = query("""SELECT i.*,b.title,b.author,u.name as student_name,u.member_id,u.phone
                    FROM issued_books i JOIN books b ON i.book_id=b.id
                    JOIN users u ON i.user_id=u.id
                    WHERE i.status='issued' ORDER BY i.issued_date DESC""", fetch=True)
    return jsonify(rows)


@issued_bp.route('/pending-fine/<int:iid>', methods=['GET'])
def pending_fine(iid):
    p = get_payload()
    if not p: return jsonify({'error':'Unauthorized'}), 401
    rec = query("SELECT * FROM issued_books WHERE id=%s", (iid,), fetchone=True)
    if not rec: return jsonify({'error':'Not found'}), 404
    today = datetime.date.today()
    delay_days = max(0, (today - rec['due_date']).days) if rec['due_date'] else 0
    fine = round(delay_days * FINE_PER_DAY, 2)
    return jsonify({'overdue_days': delay_days, 'fine': fine, 'fine_per_day': FINE_PER_DAY})

@issued_bp.route('/send-reminder', methods=['POST'])
def send_reminder():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d      = request.get_json()
    user_id = d.get('user_id')
    book_title = d.get('book_title','your book')
    due_date   = d.get('due_date','')
    query("""INSERT INTO notifications (user_id,title,message,type)
             VALUES (%s,%s,%s,'warning')""",
          (user_id, 'Return Reminder',
           f"Please return '{book_title}' by {due_date}. Fine of Rs.{FINE_PER_DAY:.0f}/day applies after due date."))
    return jsonify({'message':'Reminder sent'})
