import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Make first admin super admin
cursor.execute("""
UPDATE user
SET role='super_admin'
WHERE is_admin=1
""")

conn.commit()
conn.close()

print("✅ Roles updated")
