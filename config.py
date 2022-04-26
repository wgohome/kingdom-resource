import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    TITLE: str = "Kingdomwide Gene Expression Database"
    APP_NAME: str = os.getenv("APP_NAME", "fastapi_app")
    FASTAPI_ENV: str = os.getenv("FASTAPI_ENV", "dev")

    MONGO_SERVER: str = os.getenv("MONGO_SERVER", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", 27017))
    MONGO_USER: str | None = os.getenv("MONGO_USER")
    MONGO_PASSWORD: str | None = os.getenv("MONGO_PASSWORD")
    DATABASE_NAME: str = os.getenv(f"{APP_NAME}_{FASTAPI_ENV}", "fastapi_app")

    @property
    def DATABASE_URL(self):
        if self.MONGO_USER == "" or self.MONGO_PASSWORD == "":
            return f"mongodb://{self.MONGO_SERVER}:{self.MONGO_PORT}"
        return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_SERVER}:{self.MONGO_PORT}"


settings = Settings()

__all__ = ["settings"]
