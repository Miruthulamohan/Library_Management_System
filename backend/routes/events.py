"""Events routes"""
import jwt
from flask import Blueprint, request, jsonify
from db import query
from datetime import datetime, date, timedelta

events_bp = Blueprint('events', __name__)
SECRET = 'lms-library-secret-2024'

def normalize_date(raw_date):
    if not raw_date:
        return None
    try:
        datetime.strptime(raw_date, '%Y-%m-%d')
        return raw_date
    except ValueError:
        return None

def normalize_time(raw_time):
    if not raw_time:
        return None
    # HTML time input usually sends HH:MM; normalize for MySQL TIME.
    candidate = f"{raw_time}:00" if len(raw_time) == 5 else raw_time
    try:
        datetime.strptime(candidate, '%H:%M:%S')
        return candidate
    except ValueError:
        return None

def get_payload():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '): return None
    try: return jwt.decode(auth[7:], SECRET, algorithms=['HS256'])
    except: return None

@events_bp.route('/', methods=['GET'])
def get_events():
    rows = query("SELECT * FROM events ORDER BY event_date DESC", fetch=True) or []

    def serialize_value(v):
        # MySQL returns DATE/DATETIME/TIME as python date/datetime/timedelta.
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, timedelta):
            total_seconds = int(v.total_seconds())
            hh = total_seconds // 3600
            mm = (total_seconds % 3600) // 60
            ss = total_seconds % 60
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        return v

    serialized = []
    for row in rows:
        # query(..., fetch=True) returns dict rows because cursor(dictionary=True)
        serialized.append({k: serialize_value(v) for k, v in (row or {}).items()})

    return jsonify(serialized)

@events_bp.route('/', methods=['POST'])
def create_event():
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    d = request.get_json() or {}
    title = (d.get('title') or '').strip()
    if not title:
        return jsonify({'error':'Title is required'}), 400
    event_date = normalize_date((d.get('event_date') or '').strip())
    event_time = normalize_time((d.get('event_time') or '').strip())
    if (d.get('event_date') or '').strip() and event_date is None:
        return jsonify({'error':'Invalid event date format'}), 400
    if (d.get('event_time') or '').strip() and event_time is None:
        return jsonify({'error':'Invalid event time format'}), 400
    venue = (d.get('venue') or '').strip() or None
    description = (d.get('description') or '').strip() or None

    # events.event_date is nullable in schema, but some DB setups may be stricter.
    # Default to today's date/time when the admin leaves them blank.
    if event_date is None:
        event_date = date.today().isoformat()
    if event_time is None:
        event_time = '00:00:00'

    try:
        eid = query("""INSERT INTO events (title,description,event_date,event_time,venue)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (title, description, event_date, event_time, venue), lastrowid=True)
    except Exception as e:
        return jsonify({'error': f'Failed to create event: {str(e)}'}), 500

    if not eid:
        return jsonify({'error': 'Event insert failed — no ID returned'}), 500

    # Notify all students.
    students = query("SELECT id FROM users WHERE role='student'", fetch=True) or []
    notif_title   = f"New Event: {title}"
    notif_message = (f"{description} — " if description else '') +                     f"Date: {event_date or 'TBD'}" +                     (f", Time: {event_time}" if event_time else '') +                     (f", Venue: {venue}" if venue else '')
    sent = 0
    failed = 0
    for s in students:
        try:
            query("""INSERT INTO notifications (user_id,title,message,type)
                     VALUES (%s,%s,%s,'info')""",
                  (s['id'], notif_title, notif_message))
            sent += 1
        except Exception:
            failed += 1

    return jsonify({'message':'Event created','id':eid,'notifications_sent':sent,'notifications_failed':failed}), 201

@events_bp.route('/<int:eid>', methods=['DELETE'])
def delete_event(eid):
    p = get_payload()
    if not p or p['role'] != 'admin': return jsonify({'error':'Unauthorized'}), 401
    query("DELETE FROM events WHERE id=%s", (eid,))
    return jsonify({'message':'Event deleted'})
