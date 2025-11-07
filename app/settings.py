from pydantic import BaseSettings, AnyHttpUrl

class Settings(BaseSettings):
    CORE_URL: AnyHttpUrl = "http://host.docker.internal:8080"
    VRF_URL: AnyHttpUrl = "http://host.docker.internal:8081"
    DEMO_API_KEY: str = "demo"
    RATE_LIMIT_RPS: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
