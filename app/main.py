from fastapi import FastAPI

from config import settings
from .routes.api.v1 import species

app = FastAPI(
    title=settings.TITLE
)
app.include_router(species.router)


@app.get("/about")
def get_about():
    return {"about": f"Welcome to {settings.TITLE}!"}
