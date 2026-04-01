"""
FastAPI application entry point
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio

from app.config import settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.routers import (
    auth_router, families_router, shopping_router,
    expenses_router, incomes_router, currencies_router,
    chores_router, products_router, trips_router, users_router,
    export_router, admin_router, todos_router
)
from app.socket.handlers import sio, register_socket_handlers
from app.scheduler import start_scheduler, shutdown_scheduler
from app.utils.seed_data import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("Starting up Family Hub Backend...")
    await init_db()
    
    # Seed global default data (currencies, exchange rates)
    async with AsyncSessionLocal() as db:
        try:
            await seed_all(db)
        except Exception as e:
            print(f"Warning: Could not seed default data: {e}")
    
    register_socket_handlers()
    start_scheduler()
    print("Application started successfully!")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    shutdown_scheduler()
    await close_db()
    print("Application shut down successfully!")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="家庭管理应用后端API - Kawaii Family Hub",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Ensure upload directory exists and mount static files
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.UPLOAD_PUBLIC_BASE_URL,
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
api_prefix = "/api/v1"

app.include_router(auth_router, prefix=api_prefix)
app.include_router(families_router, prefix=api_prefix)
app.include_router(shopping_router, prefix=api_prefix)
app.include_router(expenses_router, prefix=api_prefix)
app.include_router(incomes_router, prefix=api_prefix)
app.include_router(currencies_router, prefix=api_prefix)
app.include_router(chores_router, prefix=api_prefix)
app.include_router(products_router, prefix=api_prefix)
app.include_router(trips_router, prefix=api_prefix)
app.include_router(users_router, prefix=api_prefix)
app.include_router(export_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)
app.include_router(todos_router, prefix=api_prefix)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


# Create Socket.io ASGI app
socket_app = socketio.ASGIApp(sio, app)


# For running with uvicorn
def create_app():
    """Factory function for creating the app"""
    return socket_app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:socket_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
