import time
import psycopg
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

while True:
    try:
        conn = psycopg.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )

        cur = conn.cursor()
        cur.execute("SELECT 1;")

        conn.close()

        print("✅ Database is fully ready!")
        break

    except Exception as e:
        print("⏳ Waiting for database...", e)
        time.sleep(3)
