import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE user
ADD COLUMN role VARCHAR(20) DEFAULT 'customer'
""")

conn.commit()
conn.close()

print("✅ role column added")
