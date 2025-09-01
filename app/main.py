import logging
import random
import time
from fastapi import FastAPI, Depends, HTTPException
from opentelemetry import trace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from uuid import UUID

from app.core.telemetry import setup_telemetry
from app.domain.models import User
from app.domain.repositories import ClickHouseUserRepository
from app.use_cases.user_use_cases import UserUseCases

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Database setup
DATABASE_URL = "clickhouse+native://otel:otel@clickhouse:9000/otel"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application")
    yield
    # Shutdown
    logger.info("Shutting down application")

app = FastAPI(title="OpenTelemetry Demo - Backend Only", lifespan=lifespan)

# Setup OpenTelemetry
tracer_provider, logger_provider = setup_telemetry(app, "fastapi-app")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_repository(db = Depends(get_db)):
    return ClickHouseUserRepository(db)

def get_user_use_cases(user_repository: ClickHouseUserRepository = Depends(get_user_repository)):
    return UserUseCases(user_repository)

# Routes
@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "OpenTelemetry Demo API - Backend Only"}

@app.post("/users", response_model=User)
async def create_user(
    name: str, 
    email: str, 
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    with trace.get_tracer(__name__).start_as_current_span("create_user") as span:
        span.set_attribute("user.name", name)
        span.set_attribute("user.email", email)
        
        # Simulate some processing time
        processing_time = random.uniform(0.1, 0.5)
        time.sleep(processing_time)
        span.set_attribute("processing.time", processing_time)
        
        logger.info(f"Creating user: {name}, {email}")
        try:
            user = use_cases.create_user(name, email)
            logger.info(f"User created successfully: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            span.record_exception(e)
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    with trace.get_tracer(__name__).start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)
        
        # Simulate some processing time
        processing_time = random.uniform(0.05, 0.2)
        time.sleep(processing_time)
        span.set_attribute("processing.time", processing_time)
        
        logger.info(f"Fetching user: {user_id}")
        user = use_cases.get_user(UUID(user_id))
        if user:
            logger.info(f"User found: {user_id}")
            return user
        else:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

@app.get("/users", response_model=list[User])
async def get_all_users(use_cases: UserUseCases = Depends(get_user_use_cases)):
    with trace.get_tracer(__name__).start_as_current_span("get_all_users"):
        # Simulate some processing time
        processing_time = random.uniform(0.1, 0.3)
        time.sleep(processing_time)
        
        logger.info("Fetching all users")
        users = use_cases.get_all_users()
        logger.info(f"Found {len(users)} users")
        return users

# Additional endpoints to generate more telemetry data
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}

@app.get("/slow")
async def slow_endpoint():
    with trace.get_tracer(__name__).start_as_current_span("slow_endpoint"):
        # Simulate a slow endpoint
        delay = random.uniform(0.5, 3.0)
        time.sleep(delay)
        logger.warning(f"Slow endpoint took {delay:.2f} seconds")
        return {"message": f"This endpoint was slow: {delay:.2f}s"}

@app.get("/error-test")
async def error_test():
    with trace.get_tracer(__name__).start_as_current_span("error_test"):
        # Simulate occasional errors
        if random.random() < 0.3:  # 30% chance of error
            logger.error("Simulated error occurred")
            raise HTTPException(status_code=500, detail="Simulated error")
        logger.info("Error test endpoint succeeded")
        return {"message": "No error this time"}

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    # This would typically be handled by OpenTelemetry auto-instrumentation
    return {"message": "Metrics are exported via OpenTelemetry"}