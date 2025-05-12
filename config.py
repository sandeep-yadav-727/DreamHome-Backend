from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    DATABASE_URL:str

    class Config:
        env_file = ".env"

settings = Settings()
