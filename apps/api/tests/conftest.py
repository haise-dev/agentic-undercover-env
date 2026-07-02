import os

# Set mock environment variables before importing any application code
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["APP_ENV"] = "test"
