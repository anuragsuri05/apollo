import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import APP_NAME
from .db import init_db
from .routers import auth, contribute, organizations, people, sequences, usage, workspace

app = FastAPI(title=APP_NAME, version="0.1.0", description="Open, self-hosted B2B contact platform (Apollo-compatible API).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False)


@app.on_event("startup")
def _startup():
    init_db()


@app.middleware("http")
async def rate_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in getattr(request.state, "rl_headers", {}).items():
        response.headers[k] = v
    return response


@app.exception_handler(429)
async def _429(request, exc):
    return JSONResponse(status_code=429, content={"error": "rate_limit_exceeded"}, headers=getattr(exc, "headers", None) or {})


for r in (auth, people, organizations, workspace, sequences, usage, contribute):
    app.include_router(r.router)

STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True, "app": APP_NAME}
