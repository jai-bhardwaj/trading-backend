import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not set in environment.")
    exit(1)

engine = create_engine(db_url)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1;"))
        print("✅ Database connection successful.")
except OperationalError as e:
    print(f"❌ Database connection failed: {e}")
    exit(1) 