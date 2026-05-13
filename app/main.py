import fastapi 
from app.config import config
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from dotenv import load_dotenv
from app.api.routes import router as api_router
from app.services.memory_service import create_session_id

load_dotenv()
app = fastapi.FastAPI()

# handled in lambda 
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=config.ORIGINS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
    
# )

@app.middleware("http")
async def check_for_session_id(request: fastapi.Request, call_next):
    print("Checking for session ID in middleware...")
    session_id = None
    if request.url.path.startswith("/api/v1/advanced-chat"):
        session_id = request.cookies["session_id"] if "session_id" in request.cookies else None
        if not session_id:
            session_id = create_session_id()
        request.state.session_id = session_id
    response = await call_next(request)
    if session_id:
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=86400, samesite="none", secure=True)
    return response


@app.get("/")
def read_root():
    return {"message": "Welcome to RAG API!"}

@app.get("/health")
def read_health():
    return {"status": "healthy"}

app.include_router(
    prefix="/api/v1",
    router=api_router,
)


handler = Mangum(app,lifespan="off")