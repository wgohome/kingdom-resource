from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from .routes.api.v1 import (
    species,
    genes,
    gene_annotations,
    sample_annotations,
    users,
)
# from app.routes.users import router as user_router

app = FastAPI(title=settings.TITLE)
# API endpoints
app.include_router(species.router)
app.include_router(genes.router)
app.include_router(gene_annotations.router)
app.include_router(sample_annotations.router)
app.include_router(users.router)
# Templates
# app.include_router(user_router)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/about")
def get_about():
    return {"about": f"Welcome to {settings.TITLE}!"}
