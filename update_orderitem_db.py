import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE order_item
ADD COLUMN food_id INTEGER
""")

conn.commit()
conn.close()

print("✅ food_id added to OrderItem")
