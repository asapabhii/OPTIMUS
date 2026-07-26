"""Viewer context — every retrieval is on behalf of exactly one viewer.

The viewer is the specific human asking a question.
Every retrieval is permission-filtered at query time,
for the specific viewer (P21, REQ-7.1).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Viewer(BaseModel):
    """The person using the system. Every query is on their behalf."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: str
    display_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ViewerContext(BaseModel):
    """Runtime context for a viewer's request.

    Injected into every API request via middleware.
    Used to set RLS policies and filter all queries.
    """

    viewer_id: uuid.UUID
    visible_source_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Sources this viewer currently has access to",
    )
    nango_connection_ids: dict[str, str] = Field(
        default_factory=dict,
        description="Map of provider_type -> nango_connection_id for live reads",
    )
