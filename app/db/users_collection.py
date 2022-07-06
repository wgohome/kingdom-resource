from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import (
    Cookie,
    Depends,
    HTTPException,
    Security,
    status,
)
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from h11 import Data
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr, ValidationError
from pymongo.database import Database

from app.db.setup import get_collection, get_db
from app.models.user import Token, TokenData, User, UserDoc, UserOut, UserProcessed
from config import settings


#
# DB access functions
#

def find_all_users(db: Database) -> list[UserOut]:
    USERS_COLL = get_collection(UserDoc, db)
    cursor = USERS_COLL.find({})
    results = []
    for user_dict in cursor:
        _ = user_dict.pop("hashed_pw")
        results.append(UserOut(**user_dict))
    return results


def find_user_from_db(email: str, db: Database) -> UserOut:
    # Only call this function if authenticated
    USERS_COLL = get_collection(UserDoc, db)
    user_dict = USERS_COLL.find_one({"email": email})
    if user_dict is None:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user_dict.pop("hashed_pw")
    return UserOut(**user_dict)


def create_user(user: User, db: Database) -> UserOut:
    USERS_COLL = get_collection(UserDoc, db)
    user_proc = UserProcessed(**user.dict_for_db(), hashed_pw=settings.ADMIN_PW.get_secret_value())
    user_dict = user_proc.dict_for_db()
    _ = USERS_COLL.insert_one(user_dict)
    user_dict.pop("hashed_pw")
    return UserOut(**user_dict)


def delete_user(id: ObjectId, db: Database) -> UserOut | None:
    USERS_COLL = get_collection(UserDoc, db)
    user_dict = USERS_COLL.find_one_and_delete({"_id": id})
    if user_dict is None:
        return None
    user_dict.pop("hashed_pw")
    return UserOut(**user_dict)


#
# Auth related functions
#

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/token",
    scopes={
        # "admin": "Has write access and user management",
        # "staff": "Has write access"
    },
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(email: str, password: str, db: Database) -> UserOut:
    USERS_COLL = get_collection(UserDoc, db)
    user_dict = USERS_COLL.find_one({"email": email})
    if user_dict is None:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user = UserDoc(**user_dict)
    if not verify_password(password, user.hashed_pw):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    user_dict.pop("hashed_pw")
    return UserOut(**user_dict)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_user_by_scope(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_db),
) -> UserOut:
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=EmailStr(email))
    except (JWTError, ValidationError):
        raise credentials_exception
    user = find_user_from_db(email=str(token_data.username), db=db)
    if user is None:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


def get_current_user_no_scope(
    current_user: UserOut = Security(get_user_by_scope, scopes=[])
) -> UserOut:
    return current_user


def get_admin_user(
    current_user: UserOut = Depends(get_current_user_no_scope)
) -> UserOut:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions"
        )
    return current_user


def get_user_by_cookie(authorization: str | None = Cookie(None), db: Database = Depends(get_db)) -> UserOut:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if authorization is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            authorization.split()[1],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception
    user = find_user_from_db(email=email, db=db)
    if user is None:
        raise credentials_exception
    return user


def get_admin_by_cookie(user: UserOut = Depends(get_user_by_cookie)) -> UserOut:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions"
        )
    return user


def verify_api_key(api_key: str | None = None, db: Database = Depends(get_db)) -> bool:
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate api_key credentials"
        )
    USERS_COLL = get_collection(UserDoc, db)
    user_dict = USERS_COLL.find_one({"api_key": api_key},  {"_id": 1})
    if user_dict is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate api_key credentials"
        )
    return True
