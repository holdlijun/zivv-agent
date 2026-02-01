import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import config

def get_db_connection():
    return psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)
