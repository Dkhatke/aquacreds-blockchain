from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.api.v1.endpoints import router as v1_router
from app.api.v1.projects import router as projects_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.auth import router as auth_router
from app.api.v1.mrv import router as mrv_router
from app.api.v1.admin import router as admin_router
from app.api.v1.blockchain_routes import router as blockchain_router

# Startup tasks
from app.core.init_db import create_indexes_and_validators


app = FastAPI(title="AquaCreds Backend")

# ---------------------------------------------------------
# CORS (Expo Needs Fully Open During Development)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Development only — unrestricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------
app.include_router(v1_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(mrv_router, prefix="/api/v1")

# ⭐ NEW ADMIN API (All Admin Operations)
app.include_router(admin_router, prefix="/api/v1/admin")

# ⭐ Blockchain Interaction API
app.include_router(blockchain_router, prefix="/api/v1/blockchain")

# ---------------------------------------------------------
# Startup (ENSURE INDEXES ARE CREATED)
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    try:
        await create_indexes_and_validators()
        print("DB indexes/validators ensured")
    except Exception as e:
        print("DB init failed:", e)

# ---------------------------------------------------------
# Test + Root Endpoints
# ---------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "AquaCreds Backend"}

@app.get("/test")
def test():
    return {"message": "Backend Working!"}
