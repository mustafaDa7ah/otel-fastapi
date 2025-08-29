import os
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def setup_telemetry(app, service_name):
    # Resource
    resource = Resource.create({"service.name": service_name})
    
    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # OTLP Exporter
    otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"))
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    
    otlp_log_exporter = OTLPLogExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/logs"))
    log_processor = BatchLogRecordProcessor(otlp_log_exporter)
    logger_provider.add_log_record_processor(log_processor)
    
    # Set up logging handler
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    
    # Instrumentations
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    # Create a meter
    meter = metrics.get_meter(__name__)
    
    # Create counters
    request_counter = meter.create_counter(
        "http_requests_total",
        description="Total HTTP requests",
    )
    
    # Create histograms
    request_duration = meter.create_histogram(
        "http_request_duration_seconds",
        description="HTTP request duration in seconds",
    )
    
    return tracer_provider, logger_provider