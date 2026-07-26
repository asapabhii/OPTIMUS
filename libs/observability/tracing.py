"""OpenTelemetry tracing setup → Grafana Cloud.

Every vendor call, every database query, every Plane A/B operation
gets a trace span. Correlation IDs propagate across service boundaries.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from libs.config.settings import get_settings


def setup_tracing() -> None:
    """Initialize OTel tracing with Grafana Cloud OTLP exporter."""
    settings = get_settings()

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.grafana_otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.grafana_otlp_endpoint,
            headers={
                "Authorization": f"Basic {settings.grafana_otlp_token.get_secret_value()}"
            },
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI and HTTPX
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a named tracer for manual span creation."""
    return trace.get_tracer(name, "0.1.0")
