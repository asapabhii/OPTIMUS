"""OpenTelemetry tracing setup -> Grafana Cloud.

Every vendor call, every database query, every Plane A/B operation
gets a trace span. Correlation IDs propagate across service boundaries.
"""

from __future__ import annotations

import base64

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

    endpoint = settings.grafana_otlp_endpoint
    token = settings.grafana_otlp_token.get_secret_value()

    if endpoint and token:
        try:
            # Grafana Cloud OTLP uses the token directly as the
            # Authorization header value. The token format is:
            # glc_... (base64 encoded JSON with instance/key info)
            # The correct auth is: Basic base64(instanceId:token)
            # But Grafana's glc_ tokens are self-contained — use as-is.
            instance_id = settings.otel_service_name

            # Build Basic auth: base64(instanceId:apiKey)
            # For Grafana Cloud OTLP, the instance ID comes from the token
            # The glc_ token IS the api key
            auth_value = base64.b64encode(
                f"{instance_id}:{token}".encode("utf-8")
            ).decode("ascii")

            exporter = OTLPSpanExporter(
                endpoint=endpoint,
                headers=(("authorization", f"Basic {auth_value}"),),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as e:
            # Don't crash the app if telemetry fails
            import sys
            print(f"OTLP export setup skipped: {e}", file=sys.stderr)

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI and HTTPX
    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a named tracer for manual span creation."""
    return trace.get_tracer(name, "0.1.0")
