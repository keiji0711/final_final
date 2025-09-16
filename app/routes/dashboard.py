from flask import Blueprint, render_template, session, redirect, url_for
import sqlite3

bp = Blueprint("dashboard", __name__, template_folder="../templates")
DB_PATH = "osas_attendance.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables dict-like access
    return conn

@bp.route("/dashboard")
def dashboard():
    # ---------------------------
    # Check if user is logged in
    # ---------------------------
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    user_name = session.get("username", "Officer")
    user_type = session.get("user_type", "officer")

    conn = get_db_connection()
    cur = conn.cursor()

    # ---------------------------
    # Fetch events and students
    # ---------------------------
    cur.execute("SELECT id, event_name, event_date FROM events ORDER BY event_date ASC")
    events_raw = cur.fetchall()
    total_events = len(events_raw)

    cur.execute("SELECT usn, name FROM student_info ORDER BY name ASC")
    students_raw = cur.fetchall()
    total_students = len(students_raw)

    event_ids = [e["id"] for e in events_raw]

    # ---------------------------
    # Compute global statistics
    # ---------------------------
    total_present = total_late = total_absent = 0
    if event_ids and total_students > 0:
        cur.execute(f"""
            SELECT 
                SUM(CASE WHEN time_in IS NOT NULL AND time_in != '' AND time_in != 'Absent' AND time_in != 'Late' THEN 1 ELSE 0 END) AS total_present,
                SUM(CASE WHEN time_in = 'Late' THEN 1 ELSE 0 END) AS total_late
            FROM event_attendance
            WHERE event_id IN ({','.join(['?']*len(event_ids))})
        """, event_ids)
        stats = cur.fetchone()
        total_present = stats["total_present"] or 0
        total_late = stats["total_late"] or 0
        total_records = total_students * total_events
        total_absent = total_records - (total_present + total_late)
    else:
        total_records = 0

    attendance_rate = f"{(total_present/total_records*100):.1f}%" if total_records else "0%"
    late_percentage = f"{(total_late/total_records*100):.1f}%" if total_records else "0%"
    absent_percentage = f"{(total_absent/total_records*100):.1f}%" if total_records else "0%"

    # ---------------------------
    # Compute per-event statistics
    # ---------------------------
    events = []
    for e in events_raw:
        cur.execute("""
            SELECT 
                SUM(CASE WHEN time_in IS NOT NULL AND time_in != '' AND time_in != 'Absent' AND time_in != 'Late' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN time_in = 'Late' THEN 1 ELSE 0 END) AS late
            FROM event_attendance
            WHERE event_id = ?
        """, (e["id"],))
        event_stats = cur.fetchone()
        present = event_stats["present"] or 0
        late = event_stats["late"] or 0
        absent = total_students - (present + late)

        events.append({
            "id": e["id"],
            "event_name": e["event_name"],
            "event_date": e["event_date"],
            "total_students": total_students,
            "present": present,
            "late": late,
            "absent": absent
        })

    conn.close()

    return render_template(
        "dashboard.html",
        user_name=user_name,
        user_type=user_type,
        events=events,
        total_present=total_present,
        total_late=total_late,
        total_absent=total_absent,
        attendance_rate=attendance_rate,
        late_percentage=late_percentage,
        absent_percentage=absent_percentage,
        total_students=total_students,
        total_events=total_events
    )
