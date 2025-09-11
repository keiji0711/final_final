import sqlite3

# ==================================================
# Connect to SQLite database (creates if not exists)
# ==================================================
conn = sqlite3.connect("osas_attendance.db")
cursor = conn.cursor()

# Enable foreign key enforcement
conn.execute("PRAGMA foreign_keys = ON;")

# ==================================================
# Create Tables
# ==================================================

# Events table
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    semester TEXT NOT NULL
)
""")

# Student info table
cursor.execute("""
CREATE TABLE IF NOT EXISTS student_info (
    usn TEXT PRIMARY KEY,          -- Use TEXT to safely store long IDs like 22000745800
    name TEXT NOT NULL,
    course TEXT NOT NULL,
    contact TEXT
)
""")

# Event attendance table
cursor.execute("""
CREATE TABLE IF NOT EXISTS event_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    usn TEXT NOT NULL,
    date TEXT NOT NULL,
    time_in TEXT,
    time_out TEXT,
    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
    FOREIGN KEY (usn) REFERENCES student_info (usn) ON DELETE CASCADE
)
""")

# Commit structure
conn.commit()
print("✅ Database and tables created successfully.")

# Close connection
conn.close()