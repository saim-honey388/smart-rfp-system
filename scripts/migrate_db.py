import sqlite3

# Connect to the database
conn = sqlite3.connect('rfp.db')
cursor = conn.cursor()

# New columns to add
columns = [
    ("experience", "TEXT"),
    ("methodology", "TEXT"),
    ("warranties", "TEXT"),
    ("timeline_details", "TEXT")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE proposals ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError as e:
        print(f"Column {col_name} might already exist: {e}")

conn.commit()
conn.close()
print("Migration complete.")
