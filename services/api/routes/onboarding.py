"""Onboarding journey (J1) — intent to connector recommendations."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class IntentRequest(BaseModel):
    viewer_id: str
    intent: str


class ConnectorRecommendation(BaseModel):
    provider_type: str
    display_name: str
    reason: str


class IntentResponse(BaseModel):
    intent: str
    recommended: list[ConnectorRecommendation]


INTENT_BUNDLES: dict[str, list[ConnectorRecommendation]] = {
    "renewal": [
        ConnectorRecommendation(provider_type="hubspot", display_name="HubSpot", reason="Track deal renewals, contract dates, and account health"),
        ConnectorRecommendation(provider_type="google-mail", display_name="Gmail", reason="Surface renewal-related email threads and commitments"),
        ConnectorRecommendation(provider_type="google-sheet", display_name="Google Sheets", reason="Renewal trackers and account health sheets"),
    ],
    "client": [
        ConnectorRecommendation(provider_type="hubspot", display_name="HubSpot", reason="Unified contact and company records"),
        ConnectorRecommendation(provider_type="google-mail", display_name="Gmail", reason="Complete communication history per client"),
        ConnectorRecommendation(provider_type="google-drive", display_name="Google Drive", reason="Client-related documents, proposals, SOWs"),
    ],
    "sales": [
        ConnectorRecommendation(provider_type="hubspot", display_name="HubSpot", reason="Pipeline deals, stages, and close dates"),
        ConnectorRecommendation(provider_type="google-mail", display_name="Gmail", reason="Prospect communication threads"),
        ConnectorRecommendation(provider_type="google-sheet", display_name="Google Sheets", reason="Compensation plans, territory maps, forecasts"),
    ],
    "support": [
        ConnectorRecommendation(provider_type="hubspot", display_name="HubSpot", reason="Link support issues to account health"),
        ConnectorRecommendation(provider_type="google-mail", display_name="Gmail", reason="Customer escalation email threads"),
        ConnectorRecommendation(provider_type="slack", display_name="Slack", reason="Internal support channel conversations"),
    ],
}


@router.post("/onboarding/intent", response_model=IntentResponse)
async def submit_intent(request: IntentRequest) -> IntentResponse:
    recommendations = INTENT_BUNDLES.get(
        request.intent,
        INTENT_BUNDLES["client"],
    )
    return IntentResponse(
        intent=request.intent,
        recommended=recommendations,
    )
