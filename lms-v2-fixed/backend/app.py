"""Library Management System - Main App"""
import os, io
from flask import Flask, send_from_directory, request, send_file
from flask_cors import CORS
from db import init_db
from routes.auth          import auth_bp
from routes.books         import books_bp
from routes.issued        import issued_bp
from routes.payments      import payments_bp
from routes.notifications import notifications_bp
from routes.events        import events_bp
from routes.dashboard     import dashboard_bp
from routes.membership    import membership_bp
from routes.visitors      import visitors_bp
from routes.feedback      import feedback_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lms-library-secret-2024'

CORS(app, origins="*", supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

app.register_blueprint(auth_bp,          url_prefix='/api/auth')
app.register_blueprint(books_bp,         url_prefix='/api/books')
app.register_blueprint(issued_bp,        url_prefix='/api/issued')
app.register_blueprint(payments_bp,      url_prefix='/api/payments')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
app.register_blueprint(events_bp,        url_prefix='/api/events')
app.register_blueprint(dashboard_bp,     url_prefix='/api/dashboard')
app.register_blueprint(membership_bp,    url_prefix='/api/membership')
app.register_blueprint(visitors_bp,      url_prefix='/api/visitors')
app.register_blueprint(feedback_bp,      url_prefix='/api/feedback')

@app.route('/api/health')
def health():
    return {'status': 'ok', 'message': 'LMS API running'}

@app.route('/api/qr')
def generate_qr():
    import qrcode
    url = request.args.get('url', 'http://127.0.0.1:5000')
    qr  = qrcode.QRCode(version=1, box_size=6, border=3,
                         error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#1e1b4b', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

@app.route('/')
def index():
    return send_from_directory(FRONTEND, 'index.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    fp = os.path.join(FRONTEND, filename)
    if os.path.isfile(fp):
        return send_from_directory(FRONTEND, filename)
    return send_from_directory(FRONTEND, 'index.html')

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

if __name__ == '__main__':
    init_db()
    print(f"\n  Frontend : {FRONTEND}")
    print(f"  Exists   : {os.path.exists(FRONTEND)}")
    print(f"  URL      : http://127.0.0.1:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
