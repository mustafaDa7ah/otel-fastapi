# app/main.py
import logging, random, time, os
from uuid import UUID, uuid4
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Request

from opentelemetry import trace, metrics

from app.core.telemetry import setup_telemetry, get_logger_with_context
from app.domain.models import User
from app.use_cases.user_use_cases import UserUseCases
from app.infrastructure.repositories import MockUserRepository
from app.infrastructure.kafka_producer import kafka_producer

# Use the context-aware logger
logger = get_logger_with_context(__name__)

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
    logger.info("request.start", extra={"attributes": {"path": request.url.path, "method": request.method}})
    try:
        response = await call_next(request)
        return response
    finally:
        # log end
        logger.info("request.end", extra={"attributes": {"path": request.url.path, "status_code": getattr(response, 'status_code', 0)}})
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
    attrs = {"worker.id": WORKER_ID, "number": number, "sign": "positive" if number >= 0 else "negative"}
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
        logger.info("pipeline.start", extra={"attributes": {"pipeline_id": pipeline_id, "steps": steps}})
        for ix in range(1, steps + 1):
            with tracer.start_as_current_span("pipeline.step", attributes={"step": ix}):
                delay = random.uniform(0.1, 0.6)
                time.sleep(delay)
                logger.info("pipeline.step.done", extra={"attributes": {"step": ix, "took_s": round(delay, 3)}})
        logger.info("pipeline.end", extra={"attributes": {"pipeline_id": pipeline_id}})

    dur = time.perf_counter() - start
    pipeline_duration.record(dur, attributes={"worker.id": WORKER_ID, "pipeline.id": pipeline_id})
    return {"pipeline_id": pipeline_id, "worker_id": WORKER_ID, "duration_s": round(dur, 3)}


@app.post("/pipeline/create-async")
async def create_async_pipeline(steps: int = 3):
    """Create pipeline that will be processed asynchronously"""
    pipeline_id = f"async-pl-{uuid4().hex[:8]}"
    request_id=f"request-{uuid4().hex[:8]}"
    
    with tracer.start_as_current_span("pipeline.create.async"):
        logger.info("Creating async pipeline", extra={
            # "attributes": {
                "pipeline_id": pipeline_id,
                "request_id": request_id,
                "steps": steps,
                "mode": "async",
                "worker_id": WORKER_ID
            # }
        })
        
        # Send to Kafka for async processing
        message = {
            "type": "pipeline_create",
            "pipeline_id": pipeline_id,
            "steps": steps,
            "timestamp": time.time(),
            "request_id": request_id
        }
        
        kafka_producer.produce_message(
            topic="pipelines",
            key=pipeline_id,
            value=message
        )
        
        return {
            "pipeline_id": pipeline_id,
            "status": "queued",
            "worker_id": WORKER_ID,
            "message": "Pipeline sent for async processing",
            "request_id": request_id
        }

@app.post("/message/send")
async def send_message(message: str, topic: str = "test-topic"):
    """Send a simple message to Kafka"""
    message_id = str(uuid4())
    
    with tracer.start_as_current_span("message.send"):
        logger.info("Sending message to Kafka", extra={
            "attributes": {
                "message_id": message_id,
                "topic": topic,
                "message_length": len(message)
            }
        })
        
        kafka_producer.produce_message(
            topic=topic,
            key=message_id,
            value={
                "type": "user_message",
                "content": message,
                "sender": "fastapi-service"
            }
        )
        
        return {
            "message_id": message_id,
            "status": "sent",
            "topic": topic
        }        