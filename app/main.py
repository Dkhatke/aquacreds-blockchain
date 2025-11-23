from fastapi import FastAPI
from app.api.v1.endpoints import router as v1_router
from app.api.v1.projects import router as projects_router
from app.api.v1.analysis import router as analysis_router
from app.core.init_db import create_indexes_and_validators
from app.api.v1.auth import router as auth_router
from app.api.v1.mrv import router as mrv_router

# ⭐ ADD THIS:
from app.api.v1.blockchain_routes import router as blockchain_router

app = FastAPI(title="AquaCreds Backend")

app.include_router(v1_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(mrv_router, prefix="/api/v1")

# ⭐ ADD THIS:
app.include_router(blockchain_router, prefix="/api/v1/blockchain")

@app.on_event("startup")
async def startup_event():
    try:
        await create_indexes_and_validators()
        print("DB indexes/validators ensured")
    except Exception as e:
        print("DB init failed:", e)

@app.get("/")
async def root():
    return {"status": "ok", "service": "AquaCreds Backend"}
