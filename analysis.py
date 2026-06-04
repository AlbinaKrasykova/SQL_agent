from db import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
SELECT 
    AVG(sleep_hours) AS avg_sleep,
    AVG(mood) AS avg_mood
FROM health_logs
""")

print("Sleep vs Mood:", cursor.fetchone())

cursor.execute("""
SELECT caffeine_mg, AVG(stress)
FROM health_logs
GROUP BY caffeine_mg
""")

print("Caffeine vs Stress:")
for row in cursor.fetchall():
    print(row)


    cursor.execute("""
SELECT 
    CASE 
        WHEN sleep_hours < 6 THEN 'low_sleep'
        ELSE 'normal_sleep'
    END AS sleep_category,
    AVG(stress)
FROM health_logs
GROUP BY sleep_category
""")

print("Sleep category vs stress:")
for row in cursor.fetchall():
    print(row)