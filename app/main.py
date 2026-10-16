import logging
import os
import time

from fastapi import FastAPI, Request
from mangum import Mangum

from app.api.routes import router
from app.services.memory_service import create_session_id

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
app = FastAPI(title="Portfolio RAG API")


@app.middleware("http")
async def session_and_timing(request: Request, call_next):
    started = time.perf_counter()
    session_id = None
    if request.url.path.startswith("/api/v1/advanced-chat"):
        session_id = request.cookies.get("session_id") or create_session_id()
        request.state.session_id = session_id
    try:
        response = await call_next(request)
    finally:
        logging.info("request path=%s elapsed_ms=%.1f", request.url.path, (time.perf_counter() - started) * 1000)
    if session_id:
        response.set_cookie("session_id", session_id, httponly=True, secure=True, samesite="none", max_age=86400)
    return response


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {"message": "Welcome to RAG API!"}


app.include_router(router, prefix="/api/v1")
handler = Mangum(app, lifespan="off")
