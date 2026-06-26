from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.auth import router as auth_router
from api.v1.health import router as health_router
from api.v1.reports import router as reports_router
from api.v1.scans import router as scans_router
from api.v1.targets import router as targets_router

app = FastAPI(title="SentinelAI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(targets_router, prefix="/api/v1")
app.include_router(scans_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
