"""J1 Onboarding — intent → connect → visible build → declare → prove.

Under 15 minutes or the journey has failed regardless of what got built.

The experience:
1. Ask what they want help with (NOT a wall of connector logos)
2. Recommend a bundle of 3-4 connectors from Nango's catalog
3. User connects via Nango OAuth (any integration)
4. Fast-path first-N ingestion: configurable limit, visible graph build
5. Declaration pass: 8-12 decisions, mostly inferred (REQ-12.0)
6. Background full ingestion continues after the wow moment
7. Proof answers: 3-5 questions biased toward real conflicts
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class IntentRequest(BaseModel):
    """Step 1: What does the user want help with?"""

    viewer_id: uuid.UUID
    intent: str = Field(
        description="What they want help with: renewals, inventory, client health, etc."
    )


class ConnectorBundle(BaseModel):
    """Recommended connectors based on intent."""

    provider_type: str
    display_name: str
    description: str
    icon_url: str = ""
    default_source_class: str = "authority"


class IntentResponse(BaseModel):
    """Step 1 response: recommended connector bundle."""

    recommended_connectors: list[ConnectorBundle]
    message: str


class OnboardingStatus(BaseModel):
    """Current state of the onboarding flow."""

    viewer_id: uuid.UUID
    step: str  # intent, connecting, ingesting, declaring, proving, complete
    sources_connected: int = 0
    entities_resolved: int = 0
    fast_path_progress: float = 0.0  # 0.0 to 1.0
    declarations_pending: int = 0
    declarations_completed: int = 0
    proof_questions_ready: bool = False
    elapsed_seconds: int = 0


class DeclarationItem(BaseModel):
    """A single declaration for the user to confirm or override."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    description: str
    inferred_value: str
    fact_type: str
    source_name: str
    confidence: float = 0.9
    needs_user_input: bool = False


class DeclarationPassResponse(BaseModel):
    """The declaration pass: 8-12 items, mostly inferred."""

    items: list[DeclarationItem]
    total_items: int
    inferred_count: int
    needs_input_count: int


@router.post("/onboarding/intent", response_model=IntentResponse)
async def submit_intent(request: IntentRequest) -> IntentResponse:
    """Step 1: Map user intent to a connector bundle.

    'What do you want help with?' → 3-4 relevant connectors.
    Opening with a wall of connector logos is the named onboarding failure.

    TODO: Wire to Nango catalog + intent→connector mapping.
    """
    # Example bundle for "renewals" intent
    connectors = [
        ConnectorBundle(
            provider_type="hubspot",
            display_name="HubSpot",
            description="Your CRM — deals, contacts, companies",
            default_source_class="authority",
        ),
        ConnectorBundle(
            provider_type="google_sheets",
            display_name="Google Sheets",
            description="Your spreadsheets — the numbers you track",
            default_source_class="authority",
        ),
        ConnectorBundle(
            provider_type="gmail",
            display_name="Gmail",
            description="Your email — context and evidence",
            default_source_class="evidence",
        ),
    ]
    return IntentResponse(
        recommended_connectors=connectors,
        message="Based on your interest in renewals, connect these to get started:",
    )


@router.get("/onboarding/status", response_model=OnboardingStatus)
async def get_onboarding_status(viewer_id: uuid.UUID) -> OnboardingStatus:
    """Get current onboarding progress.

    The frontend polls this to show the visible graph build
    and track the 15-minute budget.

    TODO: Wire to ingestion status + entity count + declaration state.
    """
    return OnboardingStatus(
        viewer_id=viewer_id,
        step="intent",
    )


@router.get("/onboarding/declarations", response_model=DeclarationPassResponse)
async def get_declarations(viewer_id: uuid.UUID) -> DeclarationPassResponse:
    """Step 5: The declaration pass — 8-12 decisions.

    Most classification is INFERRED, not asked (REQ-12.0):
    - Append-only sources classify themselves
    - Schema shape carries most of the rest
    - Explicit declaration is the escape hatch for ~10 items

    TODO: Wire to policy engine inference + freshness table defaults.
    """
    return DeclarationPassResponse(
        items=[],
        total_items=0,
        inferred_count=0,
        needs_input_count=0,
    )
