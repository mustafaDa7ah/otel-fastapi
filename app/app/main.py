from fastapi import FastAPI
from app.infrastructure.telemetry import setup_otel
from app.presentation.routers.pipes import router as pipes_router

def create_app() -> FastAPI:
    app = FastAPI(title="OTel Pipes Service")
    setup_otel(app)
    app.include_router(pipes_router)
    return app

app = create_app()
