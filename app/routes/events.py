from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime

bp = Blueprint("event", __name__, template_folder="../templates")

DB_PATH = "osas_attendance.db"

# --------------------------
# SocketIO instance
# --------------------------
socketio = None  # placeholder, will be injected from app

def set_socketio(sio: SocketIO):
    global socketio
    socketio = sio

# --------------------------
# Helper function
# --------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------
# Read Events
# --------------------------
@bp.route("/event")
def event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY event_date ASC")
    rows = cur.fetchall()
    conn.close()
    events = [dict(row) for row in rows]
    return render_template("events.html", events=events)

# --------------------------
# Create Event
# --------------------------
@bp.route("/add_event", methods=["POST"])
def add_event():
    event_name = request.form.get("event_name")
    event_date = request.form.get("event_date")
    semester = request.form.get("semester")
    cutoff_time = request.form.get("cutoff_time")  # NEW: get cutoff time

    if not (event_name and event_date and semester and cutoff_time):
        flash("All fields are required.", "error")
        return redirect(url_for("event.event"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (event_name, event_date, semester, cutoff_time) VALUES (?, ?, ?, ?)",
        (event_name, event_date, semester, cutoff_time)  # store cutoff_time
    )
    conn.commit()
    conn.close()

    flash(f"Event '{event_name}' added successfully!", "success")
    return redirect(url_for("event.event"))


# --------------------------
# Update Event
# --------------------------
@bp.route("/update_event/<int:event_id>", methods=["POST"])
def update_event(event_id):
    event_name = request.form.get("event_name")
    event_date = request.form.get("event_date")
    semester = request.form.get("semester")
    cutoff_time = request.form.get("cutoff_time")  # NEW

    if not (event_name and event_date and semester and cutoff_time):
        flash("All fields are required.", "error")
        return redirect(url_for("event.event"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE events SET event_name=?, event_date=?, semester=?, cutoff_time=? WHERE id=?",
        (event_name, event_date, semester, cutoff_time, event_id)  # update cutoff_time
    )
    conn.commit()
    conn.close()

    flash(f"Event '{event_name}' updated successfully!", "success")
    return redirect(url_for("event.event"))


# --------------------------
# Delete Event
# --------------------------
@bp.route("/delete_event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT event_name FROM events WHERE id=?", (event_id,))
    event = cur.fetchone()
    if event:
        cur.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
        flash(f"Event '{event['event_name']}' deleted successfully!", "success")
    else:
        flash("Event not found.", "error")
    conn.close()
    return redirect(url_for("event.event"))

# --------------------------
# View Attendance Page
# --------------------------
@bp.route("/attendance/<int:event_id>")
def view_attendance(event_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get event info
    cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = cur.fetchone()
    if not event:
        conn.close()
        flash("Event not found.", "error")
        return redirect(url_for("event.event"))

    event = dict(event)  # Convert Row to dict

    # Get all attendance records for this event
    cur.execute("SELECT * FROM event_attendance WHERE event_id=? ORDER BY date ASC", (event_id,))
    attendance = [dict(row) for row in cur.fetchall()]
    conn.close()

    return render_template(
        "event_attendance.html",
        event=event,
        attendance=attendance,
        event_id=event['id']  # pass for JS
    )


# --------------------------
# --------------------------
# Scan Attendance (Real-time) - with Cutoff, Late, Absent
# --------------------------
@bp.route("/scan_attendance", methods=["POST"])
def scan_attendance():
    global socketio
    data = request.get_json()
    if not data or "barcode" not in data or "action" not in data or "event_id" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    barcode = data["barcode"].strip()
    action = data["action"].strip()
    event_id = data["event_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    # Validate student
    cur.execute("SELECT usn, name FROM student_info WHERE usn=?", (barcode,))
    student = cur.fetchone()
    if not student:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    # Get event details
    cur.execute("SELECT event_date, cutoff_time FROM events WHERE id=?", (event_id,))
    event = cur.fetchone()
    if not event:
        conn.close()
        return jsonify({"error": "Event not found"}), 404

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now()

    def format_time(dt):
        return dt.strftime("%I:%M %p").lstrip("0")  # 12-hour format

    current_time_str = format_time(now)

    # Determine cutoff
    cutoff_time_str = event["cutoff_time"]
    after_cutoff = False
    if cutoff_time_str:
        cutoff_hour, cutoff_minute = map(int, cutoff_time_str.split(":"))
        cutoff_dt = now.replace(hour=cutoff_hour, minute=cutoff_minute, second=0, microsecond=0)
        if now > cutoff_dt:
            after_cutoff = True

    # Check existing attendance record
    cur.execute(
        "SELECT * FROM event_attendance WHERE usn=? AND event_id=? AND date=?",
        (barcode, event_id, today)
    )
    record = cur.fetchone()

    if action == "time_in":
        if after_cutoff:
            # After cutoff → cannot time in
            conn.close()
            return jsonify({"error": "⚠ Attendance cutoff time reached. Cannot time in."}), 400

        if record:
            conn.close()
            return jsonify({"error": "Already timed in today"}), 400

        # Normal time in
        time_in_value = current_time_str
        cur.execute(
            "INSERT INTO event_attendance (event_id, usn, date, time_in) VALUES (?, ?, ?, ?)",
            (event_id, barcode, today, time_in_value)
        )
        conn.commit()
        conn.close()

        if socketio:
            socketio.emit("attendance_update", {
                "event_id": event_id,
                "usn": student["usn"],
                "name": student["name"],
                "date": today,
                "time_in": time_in_value,
                "time_out": ""
            }, include_self=True)

        return jsonify({
            "record": {
                "usn": student["usn"],
                "name": student["name"],
                "date": today,
                "time_in": time_in_value,
                "time_out": ""
            }
        }), 200

    elif action == "time_out":
        if not record:
            # No prior time_in → insert Late in time_in and current time in time_out
            time_in_value = "Late"
            time_out_value = current_time_str
            cur.execute(
                "INSERT INTO event_attendance (event_id, usn, date, time_in, time_out) VALUES (?, ?, ?, ?, ?)",
                (event_id, barcode, today, time_in_value, time_out_value)
            )
            conn.commit()
            conn.close()

            if socketio:
                socketio.emit("attendance_update", {
                    "event_id": event_id,
                    "usn": student["usn"],
                    "name": student["name"],
                    "date": today,
                    "time_in": time_in_value,
                    "time_out": time_out_value
                }, include_self=True)

            return jsonify({
                "record": {
                    "usn": student["usn"],
                    "name": student["name"],
                    "date": today,
                    "time_in": time_in_value,
                    "time_out": time_out_value
                }
            }), 200

        # Normal time out update
        cur.execute(
            "UPDATE event_attendance SET time_out=? WHERE usn=? AND event_id=? AND date=?",
            (current_time_str, barcode, event_id, today)
        )
        conn.commit()
        conn.close()

        if socketio:
            socketio.emit("attendance_update", {
                "event_id": event_id,
                "usn": student["usn"],
                "name": student["name"],
                "date": today,
                "time_in": record["time_in"],
                "time_out": current_time_str
            }, include_self=True)

        return jsonify({
            "record": {
                "usn": student["usn"],
                "name": student["name"],
                "date": today,
                "time_in": record["time_in"],
                "time_out": current_time_str
            }
        }), 200

    else:
        conn.close()
        return jsonify({"error": "Invalid action"}), 400

