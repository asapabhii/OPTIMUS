"""OTel metrics — counters, histograms, and the three Phase-1 KPIs.

Phase-1 metrics instrumented in code:
1. time_to_proof_answer — histogram, target: <15 minutes
2. decision_prep_runs — counter per viewer per week
3. conflicts_surfaced — counter per pilot, target: >=1 in week one
"""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from libs.config.settings import get_settings


def setup_metrics() -> None:
    """Initialize OTel metrics with Grafana Cloud OTLP exporter."""
    settings = get_settings()

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
        }
    )

    if settings.grafana_otlp_endpoint:
        exporter = OTLPMetricExporter(
            endpoint=settings.grafana_otlp_endpoint,
            headers={
                "Authorization": f"Basic {settings.grafana_otlp_token.get_secret_value()}"
            },
        )
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
        provider = MeterProvider(resource=resource, metric_readers=[reader])
    else:
        provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(provider)


def get_meter(name: str) -> metrics.Meter:
    """Get a named meter for creating instruments."""
    return metrics.get_meter(name, "0.1.0")


# ─────────────────────────────────────────────────────────────
# Phase-1 KPI instruments — the only three metrics that matter
# ─────────────────────────────────────────────────────────────

_meter = metrics.get_meter("optimus.kpis", "0.1.0")

time_to_proof_answer = _meter.create_histogram(
    name="optimus.time_to_proof_answer_seconds",
    description="Time from login to first proof answer (target: <900s = 15 min)",
    unit="s",
)

decision_prep_runs = _meter.create_counter(
    name="optimus.decision_prep_runs",
    description="Decision-prep runs per viewer (target: >=2/week by week 3)",
)

conflicts_surfaced = _meter.create_counter(
    name="optimus.conflicts_surfaced",
    description="Genuine conflicts surfaced per pilot (target: >=1 in week one)",
)

# Operational metrics
live_read_latency = _meter.create_histogram(
    name="optimus.live_read_latency_ms",
    description="Plane B live read latency (target: <500ms p50)",
    unit="ms",
)

entity_resolution_precision = _meter.create_histogram(
    name="optimus.er_precision",
    description="Entity resolution auto-merge precision (target: >=0.98)",
)

belief_recomputations = _meter.create_counter(
    name="optimus.belief_recomputations",
    description="Number of belief recomputations triggered",
)
