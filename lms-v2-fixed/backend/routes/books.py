"""Books routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query

books_bp = Blueprint('books', __name__)
SECRET   = 'lms-library-secret-2024'

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@books_bp.route('/', methods=['GET'])
def get_books():
    search   = request.args.get('search','')
    category = request.args.get('category','')
    sql, params = "SELECT * FROM books WHERE 1=1", []
    if search:
        sql += " AND (title LIKE %s OR author LIKE %s OR isbn LIKE %s)"
        params += [f'%{search}%']*3
    if category:
        sql += " AND category=%s"; params.append(category)
    sql += " ORDER BY created_at DESC"
    return jsonify(query(sql, params, fetch=True))

@books_bp.route('/<int:bid>', methods=['GET'])
def get_book(bid):
    b = query("SELECT * FROM books WHERE id=%s", (bid,), fetchone=True)
    return jsonify(b) if b else (jsonify({'error':'Not found'}), 404)

@books_bp.route('/', methods=['POST'])
def add_book():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json()
    copies = int(d.get('total_copies', 1))
    bid = query("""INSERT INTO books (title,author,isbn,category,total_copies,available,cover_url,description)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['title'],d['author'],d.get('isbn'),d.get('category'),
                 copies, copies, d.get('cover_url'), d.get('description')), lastrowid=True)
    return jsonify({'message':'Book added','id':bid}), 201

@books_bp.route('/<int:bid>', methods=['PUT'])
def update_book(bid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json()
    query("""UPDATE books SET title=%s,author=%s,isbn=%s,category=%s,
             total_copies=%s,cover_url=%s,description=%s WHERE id=%s""",
          (d['title'],d['author'],d.get('isbn'),d.get('category'),
           d.get('total_copies',1),d.get('cover_url'),d.get('description'),bid))
    return jsonify({'message':'Book updated'})

@books_bp.route('/<int:bid>', methods=['DELETE'])
def delete_book(bid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    query("DELETE FROM books WHERE id=%s", (bid,))
    return jsonify({'message':'Book deleted'})

@books_bp.route('/categories', methods=['GET'])
def categories():
    rows = query("SELECT DISTINCT category FROM books WHERE category IS NOT NULL ORDER BY category", fetch=True)
    return jsonify([r['category'] for r in rows])
