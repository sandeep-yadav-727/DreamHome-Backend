# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    class Config:
        env_file = ".env"

settings = Settings()
