from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    TITLE: str = "Kingdomwide Gene Expression Omnibus"
    APP_NAME: str = "default_app"
    FASTAPI_ENV: str = "dev"
    MONGO_SERVER: str = "localhost"
    MONGO_PORT: int = 27017
    MONGO_USER: str | None = None
    MONGO_PASSWORD: str | None = None
    DATABASE_URL: str | None
    DATABASE_NAME: str = ""
    TEST_DATABASE_NAME: str = ""

    # Constants
    N_DECIMALS: int = 3
    PAGE_SIZE: int = 10

    class Config:
        env_file = ".env"
        env_file_encofing = "utf-8"

    @validator("DATABASE_NAME", pre=True, always=True)
    def set_database_name(cls, v, values):
        return f"{values['APP_NAME']}_{values['FASTAPI_ENV']}"

    @validator("TEST_DATABASE_NAME", pre=True, always=True)
    def set_test_database_name(cls, v, values):
        return f"{values['APP_NAME']}_test"

    @validator("DATABASE_URL", pre=True, always=True)
    def set_database_url(cls, v, values):
        if (
            values["MONGO_USER"] == "" or
            values["MONGO_PASSWORD"] == "" or
            values["MONGO_USER"] is None or
            values["MONGO_PASSWORD"] is None
        ):
            return f"mongodb://{values['MONGO_SERVER']}:{values['MONGO_PORT']}"
        return f"mongodb://{values['MONGO_USER']}:{values['MONGO_PASSWORD']}@{values['MONGO_SERVER']}:{values['MONGO_PORT']}"


settings = Settings()

__all__ = ["settings"]
