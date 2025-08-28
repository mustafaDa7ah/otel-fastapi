from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.settings import OTEL_SERVICE_NAME, OTEL_TRACES_URL, OTEL_METRICS_URL

def setup_otel(app):
    # Resource describes this service
    resource = Resource(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})

    # Traces
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)
    span_exporter = OTLPSpanExporter(endpoint=OTEL_TRACES_URL)
    trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=OTEL_METRICS_URL)
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument FastAPI routes
    FastAPIInstrumentor.instrument_app(app)
