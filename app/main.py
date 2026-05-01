import fastapi 
from config import config
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
from dotenv import load_dotenv

load_dotenv()

app = fastapi.FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Content-Type", "X-CSRF-Token"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to RAG API!"}

@app.get("/health")
def read_health():
    return {"status": "healthy"}

app.include_router(
    prefix="/api/v1",
    router=fastapi.APIRouter()
)


handler = Mangum(app)