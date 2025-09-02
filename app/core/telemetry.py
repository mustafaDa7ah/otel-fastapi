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

# ADD THESE METRICS IMPORTS
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

def setup_telemetry(app, service_name):
    print(f"🎯 Starting OpenTelemetry setup for: {service_name}")
    
    # Check environment variables
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318/v1/traces")
    print(f"📡 OTLP Endpoint: {otlp_endpoint}")
    print(f"🏷️ Service Name: {service_name}")
    
    # Resource
    resource = Resource.create({"service.name": service_name})
    
    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # OTLP Exporter for traces
    otlp_trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_trace_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    
    # OTLP Exporter for logs
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint.replace('/v1/traces', '/v1/logs'))
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)
    
    # METRICS SETUP - ADD THIS SECTION
    print("🔧 Setting up metrics...")
    try:
        # Create OTLP metrics exporter
        otlp_metrics_exporter = OTLPMetricExporter(
            endpoint=otlp_endpoint.replace('/v1/traces', '/v1/metrics')
        )
        
        # Create metric reader that exports periodically
        metric_reader = PeriodicExportingMetricReader(
            exporter=otlp_metrics_exporter,
            export_interval_millis=5000,  # Export every 5 seconds
        )
        
        # Create MeterProvider with the metric reader
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set the global meter provider
        metrics.set_meter_provider(meter_provider)
        print("✅ Metrics configured successfully")
        
    except Exception as e:
        print(f"❌ Metrics setup failed: {e}")
        import traceback
        traceback.print_exc()
        meter_provider = None
    
    # Set up logging handler
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    
    # Instrumentations
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    print("✅ OpenTelemetry setup completed successfully!")
    return tracer_provider, logger_provider