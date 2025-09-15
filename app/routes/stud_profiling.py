import sqlite3
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session

bp = Blueprint("stud_profiling", __name__, template_folder="../templates")

DB_PATH = "osas_attendance.db"

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

# -------------------------
# STUDENT LIST
# -------------------------
@bp.route("/stud_list")
@login_required
def stud_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT usn, name, course, contact FROM student_info")
    students = cur.fetchall()
    conn.close()
    students_list = [dict(row) for row in students]
    return render_template("stud_list.html", students=students_list, user_name=session.get("username", "Officer"))

# -------------------------
# STUDENT PROFILE
# -------------------------
@bp.route("/stud_profiling")
@login_required
def stud_profiling():
    usn = request.args.get("usn")
    if not usn:
        return "Student not found", 404

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch student info
    cur.execute("SELECT * FROM student_info WHERE usn=?", (usn,))
    student = cur.fetchone()
    if not student:
        conn.close()
        return "Student not found", 404
    student = dict(student)

    # Fetch all valid events
    cur.execute("SELECT id, event_name, event_date FROM events ORDER BY event_date DESC")
    events_all = [dict(row) for row in cur.fetchall()]
    total_events = len(events_all)

    # Count attended events
    cur.execute("""
        SELECT COUNT(DISTINCT ea.event_id) as attended_count
        FROM event_attendance ea
        INNER JOIN events e ON ea.event_id = e.id
        WHERE ea.usn=?
          AND ea.time_in IS NOT NULL
          AND ea.time_in != ''
          AND ea.time_in != 'Absent'
          AND ea.time_in != 'Late'
    """, (usn,))
    attended_count = cur.fetchone()["attended_count"]

    # Count late events
    cur.execute("""
        SELECT COUNT(DISTINCT ea.event_id) as late_count
        FROM event_attendance ea
        INNER JOIN events e ON ea.event_id = e.id
        WHERE ea.usn=?
          AND ea.time_in = 'Late'
    """, (usn,))
    late_count = cur.fetchone()["late_count"]

   # Count no timeout (only for existing events)
    cur.execute("""
        SELECT COUNT(*) as no_timeout_count
        FROM event_attendance ea
        JOIN events e ON ea.event_id = e.id
        WHERE ea.usn = ?
        AND (ea.time_in IS NOT NULL AND ea.time_in != '')  -- must have time_in
        AND (ea.time_out IS NULL OR ea.time_out = '')      -- missing time_out
    """, (usn,))

    no_timeout_count = cur.fetchone()["no_timeout_count"]

    # Missed events
    missed_count = total_events - (attended_count + late_count)

    # Build event history with proper status including no timeout
    cur.execute("""
        SELECT e.id, e.event_name, e.event_date,
               ea.time_in, ea.time_out,
               CASE
                   WHEN ea.time_in IS NULL OR ea.time_in = '' OR ea.time_in = 'Absent' THEN 'Missed'
                   WHEN ea.time_in = 'Late' THEN 'Late'
                   ELSE 'Attended'
               END as status
        FROM events e
        LEFT JOIN event_attendance ea
        ON e.id = ea.event_id AND ea.usn=?
        ORDER BY e.event_date DESC
    """, (usn,))
    event_history = [dict(row) for row in cur.fetchall()]

    conn.close()
    return render_template(
        "stud_profiling.html",
        student=student,
        attended=attended_count,
        missed=missed_count,
        late=late_count,
        no_timeout=no_timeout_count,
        events=event_history,
        user_name=session.get("username", "Officer")
    )

# -------------------------
# ADD STUDENT
# -------------------------
@bp.route("/add_student", methods=["POST"])
@login_required
def add_student():
    data = request.get_json()
    usn = data.get("usn")
    name = data.get("name")
    course = data.get("course")
    contact = data.get("contact")

    if not all([usn, name, course, contact]):
        return jsonify({"success": False, "message": "All fields are required.", "category":"error"})

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO student_info (usn, name, course, contact) VALUES (?,?,?,?)",
                    (usn, name, course, contact))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Student {name} added successfully!", "category":"success"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "USN already exists.", "category":"error"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "category":"error"})

# -------------------------
# UPDATE STUDENT
# -------------------------
@bp.route("/update_student/<string:usn>", methods=["POST"])
@login_required
def update_student(usn):
    data = request.get_json()
    name = data.get("name")
    course = data.get("course")
    contact = data.get("contact")

    if not all([name, course, contact]):
        return jsonify({"success": False, "message": "All fields are required.", "category":"error"})

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE student_info SET name=?, course=?, contact=? WHERE usn=?",
                    (name, course, contact, usn))
        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Student not found.", "category":"error"})
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Student {name} updated successfully!", "category":"success"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "category":"error"})

# -------------------------
# DELETE STUDENT
# -------------------------
@bp.route("/delete_student/<string:usn>", methods=["POST"])
@login_required
def delete_student(usn):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM student_info WHERE usn=?", (usn,))
        if cur.rowcount == 0:
            return jsonify({"success": False, "message": "Student not found.", "category":"error"})
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Student {usn} deleted successfully!", "category":"success"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e), "category":"error"})
