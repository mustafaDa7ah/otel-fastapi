# app/core/telemetry.py
import os, socket, logging, multiprocessing
from contextvars import ContextVar

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# context vars (used by a middleware you'll add in main.py)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# compute stable worker identity
_HOST = socket.gethostname()
_PID = os.getpid()
WORKER_ID = os.getenv("WORKER_ID", f"{_HOST}-{_PID}")
SERVICE_INSTANCE_ID = os.getenv("SERVICE_INSTANCE_ID", WORKER_ID)

def _root_logger_with_worker() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Ensure we don't double-attach handlers on reload
    already = any(isinstance(h, LoggingHandler) for h in logger.handlers)
    if not already:
        # This handler sends stdlib logging -> OTEL logs pipeline
        handler = LoggingHandler(level=logging.INFO, logger_provider=get_logger_provider())
        logger.addHandler(handler)

    # Filter to enrich every record with worker + per-request ids
    class _WorkerContextFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            # These become entries in LogAttributes in ClickHouse
            setattr(record, "worker_id", WORKER_ID)
            setattr(record, "service_instance_id", SERVICE_INSTANCE_ID)
            rid = request_id_ctx.get()
            if rid:
                setattr(record, "request_id", rid)
            return True

    # prevent stacking duplicate filters on reload
    if not any(isinstance(f, _WorkerContextFilter) for f in logger.filters):
        logger.addFilter(_WorkerContextFilter())
    return logger

def get_logger_provider():
    # helper so handler can reference configured provider
    from opentelemetry._logs import get_logger_provider as _g
    return _g()

def setup_telemetry(app, service_name: str = "fastapi-app"):
    # where to send OTLP (collector in docker-compose; override in env if needed)
    # examples:
    #   http://collector:4318  (docker compose service)
    #   https://<your-otel-gateway> (if sending straight to cloud)
    otlp_base = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    resource = Resource.create({
        "service.name": service_name,
        "service.instance.id": SERVICE_INSTANCE_ID,
        "worker.id": WORKER_ID,
        # add more stable tags if you want:
        # "deployment.environment": os.getenv("ENV", "dev"),
    })

    # ----- traces -----
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{otlp_base}/v1/traces")
        )
    )

    # ----- logs -----
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=f"{otlp_base}/v1/logs")
        )
    )

    # attach stdlib logging -> otel
    _root_logger_with_worker()

    # ----- metrics -----
    metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_base}/v1/metrics")
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=1000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # auto-instrument FastAPI routes into spans
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    return tracer_provider, logger_provider, meter_provider, request_id_ctx, WORKER_ID
