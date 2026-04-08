import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Mossy Chatbot Middleware"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Environment configs
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

settings = Settings()
