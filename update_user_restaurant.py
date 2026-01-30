import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE user
ADD COLUMN restaurant_id INTEGER
""")

conn.commit()
conn.close()

print("✅ restaurant_id added to user table")
