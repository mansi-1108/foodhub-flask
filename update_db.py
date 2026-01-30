import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE "order"
ADD COLUMN address TEXT
""")

cursor.execute("""
ALTER TABLE "order"
ADD COLUMN phone VARCHAR(15)
""")

conn.commit()
conn.close()

print("✅ Address & Phone columns added successfully")
