import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE food ADD COLUMN is_veg BOOLEAN DEFAULT 1")
cursor.execute("ALTER TABLE food ADD COLUMN is_bestseller BOOLEAN DEFAULT 0")

conn.commit()
conn.close()

print("✅ Food flags added")
