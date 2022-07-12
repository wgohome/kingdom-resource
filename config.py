from pydantic import BaseSettings, EmailStr, SecretStr, validator


class Settings(BaseSettings):
    TITLE: str = "Plant Gene Expression Omnibus"
    APP_NAME: str = "plant_omnibus"
    FASTAPI_ENV: str = "dev"

    SRV: bool = False
    DATABASE_NAME: str = ""
    TEST_DATABASE_NAME: str = ""
    MONGO_SERVER_AND_PORT: str = "localhost"
    DB_OPTIONS: str = ""
    MONGO_USER: str | None = None
    MONGO_PASSWORD: str | None = None
    DATABASE_URL: str | None = None

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # Seed Master admin
    ADMIN_EMAIL: EmailStr
    ADMIN_PW: SecretStr
    TEST_API_KEY: str

    # Constants
    N_DECIMALS: int = 3
    PAGE_SIZE: int = 10

    class Config:
        env_file = ".env"
        env_file_encofing = "utf-8"

    # Validators

    @validator("DATABASE_NAME", pre=True, always=True)
    def set_database_name(cls, v, values):
        if v:  # Not None nor empty string
            return v
        return f"{values['APP_NAME']}_{values['FASTAPI_ENV']}"

    @validator("TEST_DATABASE_NAME", pre=True, always=True)
    def set_test_database_name(cls, v, values):
        if v:  # Not None nor empty string
            return v
        return f"{values['APP_NAME']}_test"

    @validator("DATABASE_URL", pre=True, always=True)
    def set_database_url(cls, v, values):
        if v:  # Not None nor empty string
            return v
        connection_string = "mongodb+srv" if values["SRV"] else "mongodb"
        if values["MONGO_USER"] and values["MONGO_PASSWORD"]:
            return f"{connection_string}://{values['MONGO_USER']}:{values['MONGO_PASSWORD']}@{values['MONGO_SERVER_AND_PORT']}/?{values['DB_OPTIONS']}"
        return f"{connection_string}://{values['MONGO_SERVER_AND_PORT']}"

    @validator("ALGORITHM", pre=True, always=True)
    def set_algorithm(cls, v):
        if v is None or v == "":
            return "HSA256"
        return v.upper()


settings = Settings()

__all__ = ["settings"]
