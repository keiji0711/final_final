import sqlite3
from flask import Blueprint, render_template,redirect, request, url_for, flash, jsonify

bp = Blueprint("stud_profiling", __name__, template_folder="../templates")

def get_db_connection():
    conn = sqlite3.connect("osas_attendance.db")  # <- make sure this matches
    conn.row_factory = sqlite3.Row
    return conn

@bp.route("/stud_list")
def stud_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT usn, name, course, contact FROM student_info")
    students = cur.fetchall()
    conn.close()

    students_list = [dict(row) for row in students]
    return render_template("stud_list.html", students=students_list)


# -------------------------
# STUDENT PROFILE
# -------------------------
@bp.route("/stud_profiling")
def stud_profiling():
    usn = request.args.get("usn")
    if not usn:
        return "Student not found", 404

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM student_info WHERE usn=?", (usn,))
    student = cur.fetchone()
    conn.close()

    if not student:
        return "Student not found", 404

    return render_template("stud_profiling.html", student=dict(student))