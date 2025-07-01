from fastapi import FastAPI
from app.api import router

app = FastAPI(
    title="PDF-to-JSON API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)
