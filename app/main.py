import logging
import random
import time
from fastapi import FastAPI, Depends, HTTPException
from opentelemetry import trace
from contextlib import asynccontextmanager
from uuid import UUID

from app.core.telemetry import setup_telemetry
from app.domain.models import User
from app.infrastructure.repositories import MockUserRepository
from app.use_cases.user_use_cases import UserUseCases

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    yield
    logger.info("Shutting down application")

app = FastAPI(title="OpenTelemetry Demo", lifespan=lifespan)

# Setup OpenTelemetry with error handling
try:
    tracer_provider, logger_provider = setup_telemetry(app, "fastapi-app")
    logger.info("OpenTelemetry initialized successfully")
except Exception as e:
    logger.error(f"OpenTelemetry setup failed: {e}")
    tracer_provider, logger_provider = None, None

# Use Mock Repository
def get_user_repository():
    return MockUserRepository()

def get_user_use_cases(user_repository = Depends(get_user_repository)):
    return UserUseCases(user_repository)

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy", "opentelemetry": "enabled" if tracer_provider else "disabled"}

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.post("/users", response_model=User)
async def create_user(
    name: str, 
    email: str, 
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    logger.info(f"Creating user: {name}, {email}")
    try:
        user = use_cases.create_user(name, email)
        logger.info(f"User created successfully: {user.id}")
        return user
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ADD THIS MISSING ENDPOINT
@app.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    logger.info(f"Fetching user: {user_id}")
    try:
        user = use_cases.get_user(user_id)
        if user:
            logger.info(f"User found: {user_id}")
            return user
        else:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users", response_model=list[User])
async def get_all_users(use_cases: UserUseCases = Depends(get_user_use_cases)):
    logger.info("Fetching all users")
    users = use_cases.get_all_users()
    logger.info(f"Found {len(users)} users")
    return users

@app.get("/slow")
async def slow_endpoint():
    delay = random.uniform(0.5, 3.0)
    time.sleep(delay)
    logger.warning(f"Slow endpoint took {delay:.2f} seconds")
    return {"message": f"This endpoint was slow: {delay:.2f}s"}

@app.get("/error-test")
async def error_test():
    if random.random() < 0.3:
        logger.error("Simulated error occurred")
        raise HTTPException(status_code=500, detail="Simulated error")
    logger.info("Error test endpoint succeeded")
    return {"message": "No error this time"}