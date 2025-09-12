from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

bp = Blueprint("auth", __name__, template_folder="../templates")

DB_PATH = "osas_attendance.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------------------
# Decorator to require login
# ---------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("⚠️ Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# --- Login ---
@bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user_type = request.form.get("user_type")

        if not username or not password:
            flash("⚠️ Please fill in all fields!", "warning")
            return redirect(url_for("auth.login"))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_accounts WHERE username=? AND user_type=?", (username, user_type))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            # store session
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_type"] = user["user_type"]

            flash(f"✅ Welcome, {user['username']} ({user['user_type'].capitalize()})!", "success")

            # redirect all users to the same dashboard
            return redirect(url_for("dashboard.dashboard"))

        else:
            flash("❌ Invalid username, password, or role!", "danger")
            return redirect(url_for("auth.login"))

    return render_template("login.html")

# --- Logout ---
@bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("✅ You have been logged out.", "success")
    return redirect(url_for("auth.login"))

# --- List & Create Accounts ---
@bp.route("/create_account", methods=["GET", "POST"])
@login_required
def create_account():
    # Only allow non-officers to access account management
    if session.get("user_type") == "officer":
        flash("❌ You do not have permission to access this page.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        confirm_password = request.form.get("confirm_password").strip()
        user_type = request.form.get("user_type")

        # Check all fields
        if not all([username, password, confirm_password, user_type]):
            flash("⚠️ All fields are required!", "warning")
            conn.close()
            return redirect(url_for("auth.create_account"))

        # Password match check
        if password != confirm_password:
            flash("❌ Passwords do not match!", "danger")
            conn.close()
            return redirect(url_for("auth.create_account"))

        # Check if username already exists in user_accounts
        cur.execute("SELECT * FROM user_accounts WHERE username=?", (username,))
        existing = cur.fetchone()
        if existing:
            conn.close()
            flash("⚠️ Username already exists!", "warning")
            return redirect(url_for("auth.create_account"))

        # Check if username exists in student_info
        cur.execute("SELECT * FROM student_info WHERE usn=?", (username,))
        student_exists = cur.fetchone()
        if not student_exists:
            conn.close()
            flash(f"❌ Cannot create account. Student USN '{username}' does not exist!", "danger")
            return redirect(url_for("auth.create_account"))

        # All good → create account
        hashed_pw = generate_password_hash(password)
        cur.execute(
            "INSERT INTO user_accounts (username, password, user_type) VALUES (?, ?, ?)",
            (username, hashed_pw, user_type),
        )
        conn.commit()
        conn.close()

        flash(f"✅ Account for {username} created successfully!", "success")
        return redirect(url_for("auth.create_account"))

    # fetch all accounts
    cur.execute("SELECT * FROM user_accounts ORDER BY id DESC")
    users = cur.fetchall()
    conn.close()

    return render_template("create_account.html", users=users)

# --- Update Account ---
@bp.route("/update_account/<int:user_id>", methods=["POST"])
@login_required
def update_account(user_id):
    if session.get("user_type") == "officer":
        flash("❌ You do not have permission to update accounts.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    username = request.form.get("username").strip()
    user_type = request.form.get("user_type")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM user_accounts WHERE username=? AND id!=?", (username, user_id))
    existing = cur.fetchone()
    if existing:
        conn.close()
        flash("⚠️ Username already taken by another account!", "warning")
        return redirect(url_for("auth.create_account"))

    cur.execute(
        "UPDATE user_accounts SET username=?, user_type=? WHERE id=?",
        (username, user_type, user_id),
    )
    conn.commit()
    conn.close()

    flash("✏️ Account updated successfully!", "info")
    return redirect(url_for("auth.create_account"))

# --- Delete Account ---
@bp.route("/delete_account/<int:user_id>", methods=["POST"])
@login_required
def delete_account(user_id):
    if session.get("user_type") == "officer":
        flash("❌ You do not have permission to delete accounts.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_accounts WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Account deleted successfully!", "danger")
    return redirect(url_for("auth.create_account"))

