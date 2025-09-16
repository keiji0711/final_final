import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("osas_attendance.db")
cursor = conn.cursor()

# Delete all records from student_info
cursor.execute("DELETE FROM student_info")
conn.commit()
print("All records deleted from student_info.")

# Fetch and print the table to confirm
cursor.execute("SELECT * FROM student_info")
rows = cursor.fetchall()

if not rows:
    print("Table is now empty.")
else:
    print("Table still has records:")
    for row in rows:
        print(row)

conn.close()
