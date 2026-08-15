"""
main.py — FastAPI Application Entry Point
One-Person AI Enterprise Backend
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# โหลด environment variables
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# Import routers
from backend.routers import agents, logs, drafts, skype, telegram, settings, usage
from backend.services import log_service
from backend.models.schemas import LogCreate, LogLevel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & Shutdown events"""
    # Startup: โหลด logs เข้า cache
    log_service.load_logs_to_cache()
    log_service.write_log(LogCreate(
        agent_id="system",
        agent_name="System",
        level=LogLevel.SUCCESS,
        message="🚀 One-Person AI Enterprise เริ่มต้นระบบสำเร็จ",
    ))

    # เริ่มระบบ Telegram Background Polling Listener & Daily Scheduler (08:30 & 18:00 ICT)
    from backend.services import telegram_service, scheduler_service
    await telegram_service.start_telegram_polling()
    scheduler_service.start_scheduler()

    # สร้างโฟลเดอร์ที่จำเป็น
    for folder in ["departments", "logs", "drafts/proposals", "drafts/accounting", "drafts/contracts"]:
        (BASE_DIR / folder).mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    scheduler_service.stop_scheduler()
    telegram_service.stop_telegram_polling()

    log_service.write_log(LogCreate(
        agent_id="system",
        agent_name="System",
        level=LogLevel.INFO,
        message="⏹️ ระบบปิดทำงาน",
    ))



app = FastAPI(
    title="One-Person AI Enterprise",
    description="ระบบบริหารทีม AI สำหรับเจ้าของธุรกิจ",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(agents.router)
app.include_router(logs.router)
app.include_router(drafts.router)
app.include_router(skype.router)
app.include_router(telegram.router)
app.include_router(settings.router)
app.include_router(usage.router)

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "name": "One-Person AI Enterprise",
    }


# Serve frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA — fallback to index.html"""
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8888)),

        reload=os.getenv("DEBUG", "true").lower() == "true",
    )
