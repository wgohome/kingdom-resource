from fastapi import (
    APIRouter,
    Depends,
)
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.database import Database

from app.db.setup import get_db
from app.db.users_collection import (
    authenticate_user,
    create_access_token,
    find_all_users,
    get_admin_user,
    get_current_user_no_scope,
)
from app.models.user import Token, User, UserOut

router = APIRouter(prefix="/api/v1", tags=["oauth2"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(get_db)
):
    user: UserOut = authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db
    )
    access_token = create_access_token(
        data={
            "sub": user.email,
            "scopes": form_data.scopes
        }
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me/", response_model=UserOut)
async def get_user_me(
    current_user: UserOut = Depends(get_current_user_no_scope),
):
    # TOFIX cannot pass db as dependency to get_current_user_no_scope here
    return current_user


@router.get("/users", response_model=list[UserOut])
async def get_users(
    current_user: User = Depends(get_admin_user),
    db: Database = Depends(get_db)
):
    return find_all_users(db)
