import uuid
from pydantic import UUID4, EmailStr, Field, validator
from app.models.shared import CustomBaseModel, DocumentBaseModel, PyObjectId


class Token(CustomBaseModel):
    # This is the expected return format for the OAuth2 /token endpoint
    access_token: str
    token_type: str


class TokenData(CustomBaseModel):
    username: EmailStr | None = None
    scopes: list[str] = []


class User(CustomBaseModel):
    email: EmailStr
    role: str = "staff"
    api_key: str | None = None

    @validator("api_key", pre=True, always=True)
    def set_api_key(cls, v):
        if v is not None:
            return v
        return uuid.uuid4().hex


class UserOut(User):
    id: PyObjectId = Field(alias="_id")


class UserProcessed(User):
    hashed_pw: str


class UserDoc(User, DocumentBaseModel):
    id: PyObjectId = Field(alias="_id")
    hashed_pw: str

    class Mongo:
        collection_name: str = "users"
