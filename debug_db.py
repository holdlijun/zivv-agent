import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Connecting to: {DATABASE_URL}")

try:
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SHOW search_path;")
        print(f"Current search_path: {cur.fetchone()}")
        
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        print("Tables in public schema:")
        tables = [row[0] for row in cur.fetchall()]
        for t in tables:
            print(f" - {t}")
            
        print("\nTesting INSERT into analysis_reports...")
        try:
            # We use a dummy ID and rollback
            cur.execute("SAVEPOINT test_sp;")
            cur.execute("INSERT INTO analysis_reports (token_id, report_text) VALUES (1, 'test')")
            print("Successfully executed INSERT (unquoted)")
            cur.execute("ROLLBACK TO SAVEPOINT test_sp;")
        except Exception as e:
            print(f"Failed INSERT (unquoted): {e}")
            conn.rollback()
            
        print("\nTesting SELECT from tokens...")
        try:
            cur.execute("SELECT count(*) FROM tokens")
            print(f"Successfully SELECT from tokens: {cur.fetchone()[0]}")
        except Exception as e:
            print(f"Failed SELECT from tokens: {e}")
            conn.rollback()
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
