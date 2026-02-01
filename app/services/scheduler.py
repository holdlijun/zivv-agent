from app.core.db import get_db_connection
from app.core.config import config

def pull_jobs():
    """使用 SKIP LOCKED 实现高并发安全的任务拉取"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH cte AS (
                    SELECT id FROM cleaning_jobs
                    WHERE status = 0 AND next_run_at <= NOW()
                    ORDER BY stage ASC, next_run_at ASC, id ASC
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE cleaning_jobs
                SET status = 1, updated_at = NOW()
                WHERE id IN (SELECT id FROM cte)
                RETURNING *;
            """, (config.BATCH_SIZE,))
            jobs = cur.fetchall()
            conn.commit()
            return jobs
    finally:
        conn.close()

def get_token_details(token_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tokens WHERE id = %s", (token_id,))
            return cur.fetchone()
    finally:
        conn.close()
