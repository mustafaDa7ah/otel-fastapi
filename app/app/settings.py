import os

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "pipes-service")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
# HTTP paths are added by the exporters:
OTEL_TRACES_URL = f"{OTEL_ENDPOINT}/v1/traces"
OTEL_METRICS_URL = f"{OTEL_ENDPOINT}/v1/metrics"
