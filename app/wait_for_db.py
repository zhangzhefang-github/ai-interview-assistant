import os
import time
import pymysql

DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
# DB_NAME is not strictly needed for just checking server availability
# DB_NAME = os.getenv("DB_NAME") 

MAX_TRIES = 60
SLEEP_SECONDS = 5

print(f"--- wait_for_db.py: Starting ---")
print(f"Attempting to connect to MySQL server with the following parameters:")
print(f"  Host: {DB_HOST}")
print(f"  Port: {DB_PORT}")
print(f"  User: {DB_USER}")
print(f"  Password: {'********' if DB_PASSWORD else None}") # Mask password
# print(f"  Database Name (for initial check): {DB_NAME}") # Not checking DB_NAME existence here
print(f"----------------------------------")

for i in range(MAX_TRIES):
    try:
        print(f"Attempt {i + 1}/{MAX_TRIES}: Connecting to MySQL server {DB_HOST}:{DB_PORT}...")
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5 # Add a connection timeout
        )
        # If connection is successful, server is up.
        conn.close()
        print(f"--- wait_for_db.py: MySQL server at {DB_HOST}:{DB_PORT} is connectable. ---")
        exit(0) # Success
    except pymysql.MySQLError as e:
        print(f"--- wait_for_db.py: OperationalError (Attempt {i + 1}/{MAX_TRIES}): {e} ---")
        if i < MAX_TRIES - 1:
            print(f"Retrying in {SLEEP_SECONDS} seconds...")
            time.sleep(SLEEP_SECONDS)
        else:
            print(f"--- wait_for_db.py: Max retries reached. Could not connect to MySQL server. ---")
            exit(1) # Failure 