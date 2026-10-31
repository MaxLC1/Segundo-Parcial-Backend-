from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FashionStore AR API"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fashionstore_ar"
    API_BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

settings = Settings()
