import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and default seed data on startup
    db = SessionLocal()
    try:
        init_db(db)
        logger.info("Database schemas and seed data confirmed on application startup.")
    except Exception as e:
        logger.error(f"Startup database initialization error: {e}")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise IT Asset Discovery, Inventory, and CMDB Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Correlation ID and Request Performance Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()

    # Attach request_id to request state
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(process_time)
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({process_time}ms) [req:{request_id}]")
        return response
    except Exception as exc:
        process_time = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Unhandled exception during {request.method} {request.url.path} [req:{request_id}]: {exc}", exc_info=True)
        origin = request.headers.get("origin")
        headers = {
            "X-Request-ID": request_id,
            "X-Process-Time-Ms": str(process_time),
        }
        if origin and (origin in settings.BACKEND_CORS_ORIGINS or "*" in settings.BACKEND_CORS_ORIGINS):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Please contact the administrator.",
                "request_id": request_id,
            },
            headers=headers,
        )


# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

