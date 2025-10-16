from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/postgres"
    database_test_url: str = "postgresql+asyncpg://user:password@localhost:5432/postgres_test"
    secret_key: str = "secret"
    algorithm: str = "HS256"
    mail_username: str = "example@meta.ua"
    mail_password: str = "password"
    mail_from: str = "example@meta.ua"
    mail_port: int = 465
    mail_server: str = "smtp.meta.ua"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "password"
    cloudinary_name: str = "cloud_name"
    cloudinary_api_key: str = "api_key"
    cloudinary_api_secret: str = "api_secret"

    class Config:
        env_file = ROOT_DIR / ".env"
        extra = "allow"

settings = Settings()
