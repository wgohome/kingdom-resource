from bson import ObjectId
from fastapi import Cookie, Depends, Form, Request, APIRouter, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr
from pymongo.database import Database

from app.db.setup import get_db
from app.db.users_collection import (
    authenticate_user,
    create_access_token,
    create_user,
    find_all_users,
    get_admin_by_cookie,
    get_user_by_cookie,
)
from app.models.user import User, UserOut

router = APIRouter(tags=["users"])

templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request
):
    return templates.TemplateResponse("users/login.html", {"request": request})


@router.post("/login", response_class=RedirectResponse)
def login_user(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Database = Depends(get_db)
):
    user = authenticate_user(email, password, db)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "scopes": []
        }
    )
    response = RedirectResponse("/users", status_code=303)
    response.set_cookie(key="authorization", value=f"Bearer {access_token}")
    # response.headers["Authorization"] = f"Bearer {access_token}"
    return response


@router.get("/users", response_class=HTMLResponse)
def users_index(
    request: Request,
    admin_user: UserOut = Depends(get_admin_by_cookie),
    db: Database = Depends(get_db)
):
    users = find_all_users(db)
    return templates.TemplateResponse(
        "users/index.html",
        {
            "request": request,
            "users": users
        }
    )


@router.get("/users/new", response_class=HTMLResponse)
def users_new(
    request: Request,
    admin_user: UserOut = Depends(get_admin_by_cookie)
):
    return templates.TemplateResponse("users/new.html", {"request": request})


@router.post("/users", response_class=HTMLResponse)
def users_create(
    email: EmailStr = Form(...),
    role: str = Form(...),
    admin_user: UserOut = Depends(get_admin_by_cookie),
    db: Database = Depends(get_db)
):
    user_in = User(email=email, role=role)
    _ = create_user(user_in, db)
    return RedirectResponse("/users", status_code=303)


@router.delete("users/{id}", response_class=RedirectResponse)
def users_delete(
    id: str,
    admin_user: UserOut = Depends(get_admin_by_cookie),
    db: Database = Depends(get_db)
):
    import pdb; pdb.set_trace()
    return RedirectResponse("/users", status_code=303)
