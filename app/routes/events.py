from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session,send_file
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import pandas as pd
import io

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
# SESSION CHECK DECORATOR
# --------------------------
def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("⚠️ Please login first.", "warning")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper

# --------------------------
# Read Events
# --------------------------
@bp.route("/event")
@login_required
def event():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY event_date ASC")
    rows = cur.fetchall()
    conn.close()
    events = [dict(row) for row in rows]
    return render_template("events.html", events=events, user_name=session.get("username", "Officer"))

# --------------------------
# Create Event
# --------------------------
@bp.route("/add_event", methods=["POST"])
@login_required
def add_event():
    event_name = request.form.get("event_name")
    event_date = request.form.get("event_date")
    semester = request.form.get("semester")
    cutoff_time = request.form.get("cutoff_time")

    if not (event_name and event_date and semester and cutoff_time):
        flash("All fields are required.", "error")
        return redirect(url_for("event.event"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (event_name, event_date, semester, cutoff_time) VALUES (?, ?, ?, ?)",
        (event_name, event_date, semester, cutoff_time)
    )
    conn.commit()
    conn.close()

    flash(f"Event '{event_name}' added successfully!", "success")
    return redirect(url_for("event.event"))

# --------------------------
# Update Event
# --------------------------
@bp.route("/update_event/<int:event_id>", methods=["POST"])
@login_required
def update_event(event_id):
    event_name = request.form.get("event_name")
    event_date = request.form.get("event_date")
    semester = request.form.get("semester")
    cutoff_time = request.form.get("cutoff_time")

    if not (event_name and event_date and semester and cutoff_time):
        flash("All fields are required.", "error")
        return redirect(url_for("event.event"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE events SET event_name=?, event_date=?, semester=?, cutoff_time=? WHERE id=?",
        (event_name, event_date, semester, cutoff_time, event_id)
    )
    conn.commit()
    conn.close()

    flash(f"Event '{event_name}' updated successfully!", "success")
    return redirect(url_for("event.event"))

# --------------------------
# Delete Event
# --------------------------
@bp.route("/delete_event/<int:event_id>", methods=["POST"])
@login_required
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
@login_required
def view_attendance(event_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = cur.fetchone()
    if not event:
        conn.close()
        flash("Event not found.", "error")
        return redirect(url_for("event.event"))

    event = dict(event)

    cur.execute("""
        SELECT ea.*, si.name
        FROM event_attendance ea
        LEFT JOIN student_info si ON ea.usn = si.usn
        WHERE ea.event_id=?
        ORDER BY ea.date ASC
    """, (event_id,))
    attendance = [dict(row) for row in cur.fetchall()]
    conn.close()

    return render_template(
        "event_attendance.html",
        event=event,
        attendance=attendance,
        event_id=event['id'],
        user_name=session.get("username", "Officer")
    )

# --------------------------
# Scan Attendance (Real-time)
# --------------------------
@bp.route("/scan_attendance", methods=["POST"])
@login_required
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
    current_time_str = now.strftime("%I:%M %p").lstrip("0")  # 12-hour format

    cutoff_time_str = event["cutoff_time"]
    after_cutoff = False
    if cutoff_time_str:
        cutoff_hour, cutoff_minute = map(int, cutoff_time_str.split(":"))
        cutoff_dt = now.replace(hour=cutoff_hour, minute=cutoff_minute, second=0, microsecond=0)
        if now > cutoff_dt:
            after_cutoff = True

    # Check existing record
    cur.execute(
        "SELECT * FROM event_attendance WHERE usn=? AND event_id=? AND date=?",
        (barcode, event_id, today)
    )
    record = cur.fetchone()

    if action == "time_in":
        if after_cutoff:
            conn.close()
            return jsonify({"error": "⚠ Attendance cutoff time reached. Cannot time in."}), 400
        if record:
            conn.close()
            return jsonify({"error": "Already timed in today"}), 400

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


# --------------------------
# # Export Attendance to Excel
# --------------------------
@bp.route("/export_excel/<int:event_id>")
@login_required
def export_excel(event_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ea.usn, si.name, ea.date, ea.time_in, ea.time_out
        FROM event_attendance ea
        JOIN student_info si ON ea.usn = si.usn
        WHERE ea.event_id = ?
        ORDER BY si.name
    """, (event_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        flash("⚠ No attendance records to export.", "warning")
        return redirect(url_for("event.event"))

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=["USN", "Name", "Date", "Time In", "Time Out"])

    # Save to in-memory Excel with formatting
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance")
        workbook = writer.book
        worksheet = writer.sheets["Attendance"]

        # Header formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2E2E2E',
            'font_color': 'white',
            'border': 1
        })
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)

        # Highlight late Time In cells
        late_format = workbook.add_format({
            'bg_color': '#FFA500',  # orange
            'font_color': 'black'
        })
        for row_num, value in enumerate(df['Time In'], start=1):
            if value == 'Late':
                worksheet.write(row_num, 3, value, late_format)  # column 3 = "Time In"

    output.seek(0)
    filename = f"Attendance_Event_{event_id}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True)

