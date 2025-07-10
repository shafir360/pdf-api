from fastapi import FastAPI
from app.api import router

app = FastAPI(title="PDF API")
app.include_router(router)
