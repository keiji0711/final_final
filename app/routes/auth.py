from flask import Blueprint, render_template

# Tell Flask to look in app/templates
bp = Blueprint("auth", __name__, template_folder="../templates")

@bp.route("/")
def auth():
    events = [
        {"id": 1, "name": "Python Workshop", "date": "2025-09-12"},
        {"id": 2, "name": "AI Seminar", "date": "2025-09-15"}
    ]

    students = [
        {"id": 1, "name": "John Doe", "email": "john@example.com", "student_id": "S001", "barcode": "123456"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "student_id": "S002", "barcode": "654321"}
    ]

    return render_template("auth.html", events=events, students=students)