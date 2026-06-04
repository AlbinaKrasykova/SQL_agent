import sqlite3
import random
from datetime import datetime, timedelta

DB_NAME = "health.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,

        -- wearable data
        heart_rate INTEGER,
        hrv REAL,
        sleep_hours REAL,
        steps INTEGER,
        calories_burned INTEGER,

        -- behavioral data
        mood INTEGER,
        energy INTEGER,
        stress INTEGER,

        -- nutrition data
        calories_intake INTEGER,
        caffeine_mg INTEGER,

        meal_type TEXT
    )
    """)

def generate_row(user_id, timestamp):
    heart_rate = random.randint(55, 160)
    hrv = round(random.uniform(20, 120), 2)
    sleep_hours = round(random.uniform(4.0, 9.0), 1)
    steps = random.randint(1000, 18000)
    calories_burned = random.randint(1800, 3500)

    mood = random.randint(1, 10)
    energy = random.randint(1, 10)
    stress = random.randint(1, 10)

    calories_intake = random.randint(1500, 3200)
    caffeine_mg = random.choice([0, 50, 100, 200, 300])

    meal_type = random.choice(["breakfast", "lunch", "dinner", "snack"])

    return (
        user_id,
        timestamp,
        heart_rate,
        hrv,
        sleep_hours,
        steps,
        calories_burned,
        mood,
        energy,
        stress,
        calories_intake,
        caffeine_mg,
        meal_type
    )

def main():
    conn = get_connection()
    cursor = conn.cursor()

    create_tables(cursor)

    base_time = datetime.now()

    data = []
    for i in range(300):  # more data = better ML later
        timestamp = (base_time - timedelta(hours=i)).isoformat()
        data.append(generate_row(user_id=1, timestamp=timestamp))

    cursor.executemany("""
    INSERT INTO health_logs (
        user_id, timestamp,
        heart_rate, hrv, sleep_hours, steps, calories_burned,
        mood, energy, stress,
        calories_intake, caffeine_mg, meal_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

    conn.commit()
    conn.close()

    print("Health dataset created successfully.")

if __name__ == "__main__":
    main()