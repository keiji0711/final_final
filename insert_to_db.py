import sqlite3
import pandas as pd
import os

# Connect to SQLite database
conn = sqlite3.connect("osas_attendance.db")
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS student_info (
    usn TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    course TEXT NOT NULL,
    contact TEXT
)
""")
conn.commit()

# Ask user for Excel file path
excel_path = input("Enter Excel file path: ").strip()
excel_path = excel_path.strip('"').strip("'")  # remove quotes
excel_path = excel_path.replace("\\", "/")      # convert backslashes

if not os.path.exists(excel_path):
    print(f"File does not exist: {excel_path}")
    exit()

# Load Excel file
try:
    xls = pd.ExcelFile(excel_path)
except Exception as e:
    print(f"Error loading Excel file: {e}")
    exit()

# Loop through all sheets
for sheet_name in xls.sheet_names:
    print(f"\nInserting data from sheet: {sheet_name}")
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    # Normalize column names
    df.columns = [str(col).strip().replace('\xa0', '').upper() for col in df.columns]
    print(f"Columns detected: {list(df.columns)}")  # Preview columns

    # Map actual column names to expected ones
    column_mapping = {
        'USN/TEMPORARY': 'USN',
        'USN': 'USN',  # keep if some sheets already have correct 'USN'
        'LAST NAME': 'LAST NAME',
        'FIRST NAME': 'FIRST NAME',
        'MIDDLE NAME': 'MIDDLE NAME'
    }
    df.rename(columns=column_mapping, inplace=True)

    # Insert data into database
    for _, row in df.iterrows():
        try:
            usn = str(row['USN']).strip()
            name = f"{row['LAST NAME']} {row['FIRST NAME']} {row['MIDDLE NAME']}".strip()
            course = sheet_name
            contact = "N/A"

            cursor.execute("""
            INSERT OR IGNORE INTO student_info (usn, name, course, contact)
            VALUES (?, ?, ?, ?)
            """, (usn, name, course, contact))
        except KeyError as ke:
            print(f"Missing column in sheet '{sheet_name}': {ke}")
        except Exception as e:
            print(f"Error inserting USN {usn}: {e}")

conn.commit()
conn.close()
print("\nAll data inserted successfully!")
