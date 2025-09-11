# import sqlite3

# # Connect to the database
# conn = sqlite3.connect("osas_attendance.db")
# cursor = conn.cursor()

# # Insert sample student
# cursor.execute("""
# INSERT OR IGNORE INTO student_info (usn, name, course, contact)
# VALUES (?, ?, ?, ?)
# """, ("15001074500", "Dexter James Dedgayo", "BSCS", "dexter.james.degayo@aclcbutuan.edu.ph"))

# # Save and close
# conn.commit()
# conn.close()

# print("Student inserted successfully!")


import sqlite3

conn = sqlite3.connect("osas_attendance.db")
cursor = conn.cursor()

# Add attendance_cutoff column (if not exists)
try:
    cursor.execute("ALTER TABLE events ADD COLUMN cutoff_time TEXT")
    print("✅ Column 'cutoff_time' added to 'events' table.")
except sqlite3.OperationalError as e:
    print("⚠️", e)  # Likely means column already exists

conn.commit()
conn.close()
