# app/main.py
import logging, random, time, os
from uuid import UUID, uuid4
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request

from opentelemetry import trace, metrics

from app.core.telemetry import setup_telemetry  # <- your new function
from app.domain.models import User
from app.use_cases.user_use_cases import UserUseCases
from app.infrastructure.repositories import MockUserRepository

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    yield
    logger.info("Shutting down application")

app = FastAPI(title="OpenTelemetry Demo", lifespan=lifespan)

# --- set up telemetry first ---
tracer_provider, logger_provider, meter_provider, request_id_ctx, WORKER_ID = setup_telemetry(app, "fastapi-app")
tracer = trace.get_tracer(__name__)

# --- now metrics & counters (after meter provider is set) ---
meter = metrics.get_meter("fastapi-app")
positive_counter = meter.create_counter(
    name="positive_counter",
    description="Total number of positive numbers returned",
    unit="1",
)
negative_counter = meter.create_counter(
    name="negative_counter",
    description="Total number of negative numbers returned",
    unit="1",
)
pipeline_runs = meter.create_counter(
    name="pipeline_runs",
    description="Number of pipeline runs",
    unit="1",
)
pipeline_duration = meter.create_histogram(
    name="pipeline_duration_seconds",
    description="Duration of pipeline run in seconds",
    unit="s",
)

# --- request-id middleware (enrich logs per request) ---
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid4()))
    token = request_id_ctx.set(rid)
    # log start
    logger.info("request.start", extra={"path": request.url.path, "method": request.method})
    try:
        response = await call_next(request)
        return response
    finally:
        # log end
        logger.info("request.end", extra={"path": request.url.path, "status_code": getattr(response, 'status_code', 0)})
        request_id_ctx.reset(token)

# --- basic endpoints ---
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy", "opentelemetry": "enabled"}

@app.get("/")
async def root():
    return {"message": "API is running", "worker_id": WORKER_ID}

# simulate the exercise: positive/negative numbers + metrics + logs
@app.get("/random-number")
async def random_number():
    number = random.randint(-10, 10)
    attrs = {"attributes": {"worker.id": WORKER_ID, "number": number, "sign": "positive" if number >= 0 else "negative"}}
    if number >= 0:
        positive_counter.add(1, attributes=attrs)
        logger.info("Generated positive number", extra={"attributes": {"number": number}})
    else:
        negative_counter.add(1, attributes=attrs)
        logger.info("Generated negative number", extra={"attributes": {"number": number}})
    return {"number": number, "worker_id": WORKER_ID}

# --- pipeline demo: shows worker.id in spans, logs & metrics ---
@app.post("/pipeline/run")
async def run_pipeline(pipeline_id: Optional[str] = None, steps: int = 3):
    pipeline_id = pipeline_id or f"pl-{uuid4().hex[:8]}"
    start = time.perf_counter()
    pipeline_runs.add(1, attributes={"worker.id": WORKER_ID, "pipeline.id": pipeline_id})

    with tracer.start_as_current_span(
        "pipeline.run",
        attributes={"pipeline.id": pipeline_id, "worker.id": WORKER_ID, "steps": steps}
    ) as span:
        logger.info("pipeline.start", extra={"attributes": {"pipeline_id": pipeline_id, "steps": steps }})
        for ix in range(1, steps + 1):
            with tracer.start_as_current_span("pipeline.step", attributes={"step": ix}):
                delay = random.uniform(0.1, 0.6)
                time.sleep(delay)
                logger.info("pipeline.step.done", extra={"attributes": {"step": ix, "took_s": round(delay, 3)}})
        logger.info("pipeline.end", extra={"attributes": {"pipeline_id": pipeline_id}})

    dur = time.perf_counter() - start
    pipeline_duration.record(dur, attributes={"attributes": {"worker.id": WORKER_ID, "pipeline.id": pipeline_id}})
    return {"pipeline_id": pipeline_id, "worker_id": WORKER_ID, "duration_s": round(dur, 3)}

# --- your existing user endpoints (unchanged) ---
def get_user_repository():
    return MockUserRepository()

def get_user_use_cases(user_repository = Depends(get_user_repository)):
    return UserUseCases(user_repository)

@app.post("/users", response_model=User)
async def create_user(name: str, email: str, use_cases: UserUseCases = Depends(get_user_use_cases)):
    logger.info("Creating user", extra={"name": name, "email": email})
    try:
        user = use_cases.create_user(name, email)
        logger.info("User created successfully", extra={"user_id": str(user.id)})
        return user
    except Exception as e:
        logger.error("Error creating user", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: UUID, use_cases: UserUseCases = Depends(get_user_use_cases)):
    logger.info("Fetching user", extra={"user_id": str(user_id)})
    try:
        user = use_cases.get_user(user_id)
        if user:
            logger.info("User found", extra={"user_id": str(user_id)})
            return user
        else:
            logger.warning("User not found", extra={"user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error("Error fetching user", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users", response_model=list[User])
async def get_all_users(use_cases: UserUseCases = Depends(get_user_use_cases)):
    logger.info("Fetching all users")
    users = use_cases.get_all_users()
    logger.info("Users fetched", extra={"count": len(users)})
    return users

@app.get("/slow")
async def slow_endpoint():
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)
    logger.warning("Slow endpoint", extra={"delay_s": round(delay, 2)})
    return {"message": f"This endpoint was slow: {delay:.2f}s", "worker_id": WORKER_ID}

@app.get("/error-test")
async def error_test():
    if random.random() < 0.3:
        logger.error("Simulated error occurred")
        raise HTTPException(status_code=500, detail="Simulated error")
    logger.info("Error test endpoint succeeded")
    return {"message": "No error this time"}
