import logging
import random
import time
import os
from fastapi import FastAPI, Depends, HTTPException
from opentelemetry import trace
from contextlib import asynccontextmanager
from uuid import UUID

from app.core.telemetry import setup_telemetry
from app.domain.models import User
from app.infrastructure.repositories import ClickHouseUserRepository
from app.use_cases.user_use_cases import UserUseCases
from opentelemetry import metrics

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔧 Application starting up...")
    logger.info("Starting up application")
    yield
    logger.info("Shutting down application")

app = FastAPI(title="OpenTelemetry Demo", lifespan=lifespan)

# Debug: Check environment variables
print(f"📡 OTEL_EXPORTER_OTLP_ENDPOINT: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')}")
print(f"🏷️ OTEL_SERVICE_NAME: {os.getenv('OTEL_SERVICE_NAME')}")

# Setup OpenTelemetry with error handling
print("🔧 Attempting OpenTelemetry setup...")
try:
    tracer_provider, logger_provider = setup_telemetry(app, "fastapi-app")
    if tracer_provider:
        print("✅ OpenTelemetry initialized successfully")
        logger.info("OpenTelemetry initialized successfully")
    else:
        print("❌ OpenTelemetry setup returned None")
        logger.error("OpenTelemetry setup returned None")
except Exception as e:
    print(f"❌ OpenTelemetry setup failed: {e}")
    import traceback
    traceback.print_exc()
    tracer_provider, logger_provider = None, None

# Add after the OpenTelemetry setup
meter = metrics.get_meter(__name__)

def get_user_repository():
    return ClickHouseUserRepository()

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

# Create metrics for positive/negative numbers
positive_counter = meter.create_counter(
    "positive_numbers_total",
    description="Total number of positive numbers returned"
)
negative_counter = meter.create_counter(
    "negative_numbers_total", 
    description="Total number of negative numbers returned"
)

@app.get("/random-number")
async def random_number():
    with trace.get_tracer(__name__).start_as_current_span("random_number"):
        # Generate random number between -100 and 100
        import random
        number = random.randint(-100, 100)
        
        # Record the metric
        if number >= 0:
            positive_counter.add(1, {"number": number})
            logger.info(f"Generated positive number: {number}")
        else:
            negative_counter.add(1, {"number": number}) 
            logger.info(f"Generated negative number: {number}")
        
        return {"number": number}

# Add test endpoint for manual tracing
@app.get("/test-telemetry")
async def test_telemetry():
    print("🧪 Testing telemetry...")
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_telemetry_span") as span:
            span.set_attribute("test.attribute", "value")
            print("✅ Manual span created successfully")
            return {"status": "success", "message": "Trace created"}
    except Exception as e:
        print(f"❌ Failed to create span: {e}")
        return {"status": "error", "message": str(e)}
    
@app.get("/test-auto-trace")
async def test_auto_trace():
    # This should be automatically instrumented
    logger.info("This endpoint should be auto-instrumented")
    return {"message": "Auto instrumentation test"}