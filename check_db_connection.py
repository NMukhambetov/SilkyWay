import os
import time
import pymysql

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

for i in range(10):
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,  # <- обязательно пароль
            database=DB_NAME,
            port=DB_PORT
        )
        conn.close()
        print("✅ MySQL is ready!")
        break
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        time.sleep(3)
