from db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT * FROM health_logs LIMIT 5")
rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()