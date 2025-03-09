from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GEMINI_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    MISTRAL_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()