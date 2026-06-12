import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), '..', 'ipekgpt.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())

# Check feedback
try:
    cursor.execute("SELECT COUNT(*) FROM feedback")
    print("Feedback count:", cursor.fetchone()[0])
    cursor.execute("SELECT * FROM feedback")
    print("Feedback rows:", cursor.fetchall())
except Exception as e:
    print("Feedback error:", e)

# Check rate limits
try:
    cursor.execute("SELECT COUNT(*) FROM rate_limits")
    print("Rate limits count:", cursor.fetchone()[0])
    cursor.execute("SELECT * FROM rate_limits")
    print("Rate limits rows:", cursor.fetchall())
except Exception as e:
    print("Rate limits error:", e)

conn.close()
