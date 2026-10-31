
import os

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings

from .routes import discover, verify, contribution_plan


# Application settings
class Settings(BaseSettings):
    tinyfish_api_key: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# Create FastAPI application
app = FastAPI(
    title="Trailbit Backend",
    version="0.1.0"
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TinyFish client dependency
def get_tinyfish_client():
    from .services.tinyfish import TinyFishClient
    return TinyFishClient()


# Health check
@app.get("/health")
def health_check():
    return {"status": "ok"}


# Register API routes
app.include_router(
    discover.router,
    prefix="/api",
    dependencies=[Depends(get_tinyfish_client)]
)

app.include_router(
    verify.router,
    prefix="/api",
    dependencies=[Depends(get_tinyfish_client)]
)

app.include_router(
    contribution_plan.router,
    prefix="/api",
    dependencies=[Depends(get_tinyfish_client)]
)


# Serve frontend files
frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../frontend")
)

app.mount(
    "/",
    StaticFiles(directory=frontend_path, html=True),
    name="frontend"
)


# Run application directly
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )
