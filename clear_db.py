import sqlite3
import os

DB_NAME = "candidates.db"

def clear_databases():
    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found. Nothing to clear.")
        return

    print(f"Connecting to {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']

        for table in tables:
            print(f"Clearing table: {table}...")
            cursor.execute(f"DELETE FROM {table};")
            # Also reset any auto-increment counters
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?;", (table,))
        
        conn.commit()
        print("\nSuccessfully cleared all tables in candidates.db!")
    except Exception as e:
        conn.rollback()
        print(f"Error clearing databases: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_databases()
