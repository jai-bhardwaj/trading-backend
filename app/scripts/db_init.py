import os
from sqlalchemy import create_engine
from app.models import Base  # Adjust import if your Base is elsewhere
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not set in environment.")
    exit(1)

engine = create_engine(db_url)
try:
    Base.metadata.create_all(engine)
    print("✅ Database tables created (or already exist).")
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    exit(1) 