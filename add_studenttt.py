import sqlite3

# Connect to the database
conn = sqlite3.connect("osas_attendance.db")
cursor = conn.cursor()

# Sample students data
students = [
    ("10", "Alice Johnson", "BSCS", "alice.johnson@aclcbutuan.edu.ph"),
    ("11", "Bob Smith", "BSIT", "bob.smith@aclcbutuan.edu.ph"),
    ("12", "Charlie Reyes", "BSCS", "charlie.reyes@aclcbutuan.edu.ph"),
    ("13", "Diana Cruz", "BSIT", "diana.cruz@aclcbutuan.edu.ph"),
    ("14", "Ethan Garcia", "BSCS", "ethan.garcia@aclcbutuan.edu.ph"),
    ("15", "Fiona Lopez", "BSIT", "fiona.lopez@aclcbutuan.edu.ph"),
    ("16", "George Santos", "BSCS", "george.santos@aclcbutuan.edu.ph"),
    ("17", "Hannah Diaz", "BSIT", "hannah.diaz@aclcbutuan.edu.ph"),
    ("18", "Ian Torres", "BSCS", "ian.torres@aclcbutuan.edu.ph"),
    ("19", "Julia Navarro", "BSIT", "julia.navarro@aclcbutuan.edu.ph"),
    ("20", "Kevin Tan", "BSCS", "kevin.tan@aclcbutuan.edu.ph"),
    ("21", "Lara Mendoza", "BSIT", "lara.mendoza@aclcbutuan.edu.ph"),
    ("22", "Michael Lim", "BSCS", "michael.lim@aclcbutuan.edu.ph"),
    ("23", "Nina Velasco", "BSIT", "nina.velasco@aclcbutuan.edu.ph"),
    ("24", "Oscar Reyes", "BSCS", "oscar.reyes@aclcbutuan.edu.ph"),
]

# Insert students into student_info table
for student in students:
    cursor.execute("""
    INSERT OR IGNORE INTO student_info (usn, name, course, contact)
    VALUES (?, ?, ?, ?)
    """, student)

# Save and close
conn.commit()
conn.close()

print("15 students inserted successfully!")
