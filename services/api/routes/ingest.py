"""Data ingestion — fetch real data from connected sources via Nango proxy.

Uses LlamaCloud (LlamaParse) for document decomposition when available.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from libs.config.settings import get_settings
from libs.observability.logging import get_logger

logger = get_logger("ingest")

router = APIRouter()


class IngestResult(BaseModel):
    connection_id: str
    provider_type: str
    records_fetched: int
    entities_created: int
    errors: list[str]


class EntityRecord(BaseModel):
    id: str
    type: str
    name: str
    source: str
    source_id: str
    properties: dict[str, Any]
    fetched_at: str
    connection_id: str


# In-memory store with disk persistence — production uses Postgres
_entity_store: list[EntityRecord] = []
import pathlib as _pathlib
_ENTITY_STORE_PATH = str(
    _pathlib.Path(__file__).resolve().parents[3] / "data" / "entities.json"
)


def _load_entity_store() -> None:
    """Load entities from disk on startup."""
    import json
    import os

    if os.path.exists(_ENTITY_STORE_PATH):
        try:
            with open(_ENTITY_STORE_PATH, "r") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                _entity_store.clear()
                for item in raw:
                    _entity_store.append(EntityRecord(**item))
                logger.info("entity_store_loaded", count=len(_entity_store))
        except Exception as e:
            logger.warning("entity_store_load_failed", error=str(e))


def _persist_entity_store() -> None:
    """Persist entities to disk."""
    import json
    import os

    os.makedirs(os.path.dirname(_ENTITY_STORE_PATH), exist_ok=True)
    with open(_ENTITY_STORE_PATH, "w") as f:
        json.dump([e.model_dump() for e in _entity_store], f)


# Load on module import
_load_entity_store()


def get_entity_store() -> list[EntityRecord]:
    return _entity_store


async def _nango_proxy_get(
    secret: str,
    connection_id: str,
    provider_config_key: str,
    endpoint: str,
    params: dict | list | None = None,
) -> dict | list | None:
    """Make an authenticated API call via Nango's proxy."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.nango.dev/proxy/{endpoint}",
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Connection-Id": connection_id,
                    "Provider-Config-Key": provider_config_key,
                },
                params=params or {},
                timeout=20.0,
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(
                    "nango_proxy_failed",
                    endpoint=endpoint,
                    status=resp.status_code,
                    body=resp.text[:300],
                )
                return None
    except Exception as e:
        logger.error("nango_proxy_error", endpoint=endpoint, error=str(e))
        return None


async def _llamacloud_parse(
    file_url: str, file_name: str, mime_type: str
) -> str | None:
    """Parse a document using LlamaCloud LlamaParse API.

    Returns extracted text, or None if parsing fails or API key missing.
    """
    settings = get_settings()
    api_key = settings.llama_cloud_api_key
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Upload file URL for parsing
            resp = await client.post(
                "https://api.cloud.llamaindex.ai/api/parsing/upload",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": file_url,
                    "file_name": file_name,
                    "parsing_instruction": (
                        "Extract all text content including tables, headers, "
                        "and structured data. Preserve entity names, dates, "
                        "and numerical values."
                    ),
                    "result_type": "markdown",
                },
                timeout=30.0,
            )

            if resp.status_code not in (200, 201):
                logger.warning(
                    "llamacloud_upload_failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return None

            job = resp.json()
            job_id = job.get("id", "")
            if not job_id:
                return None

            # Step 2: Poll for completion (up to 60s)
            import asyncio

            for _ in range(12):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"https://api.cloud.llamaindex.ai/api/parsing/job/{job_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0,
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    if status_data.get("status") == "SUCCESS":
                        # Step 3: Get result
                        result_resp = await client.get(
                            f"https://api.cloud.llamaindex.ai/api/parsing/job/{job_id}/result/markdown",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=15.0,
                        )
                        if result_resp.status_code == 200:
                            result = result_resp.json()
                            return result.get("markdown", result.get("text", ""))
                    elif status_data.get("status") in ("ERROR", "FAILED"):
                        logger.warning("llamacloud_parse_failed", job=job_id)
                        return None

            logger.warning("llamacloud_parse_timeout", job=job_id)
            return None
    except Exception as e:
        logger.warning("llamacloud_error", error=str(e))
        return None


def _parse_email_address(raw: str) -> tuple[str, str]:
    """Extract name and email from 'Name <email>' format."""
    match = re.match(r"^(.*?)\s*<(.+?)>$", raw.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return name or email.split("@")[0], email
    return raw.strip(), raw.strip()


def _extract_people_from_emails(
    entities: list[EntityRecord], connection_id: str
) -> list[EntityRecord]:
    """Extract unique people (contacts) from email metadata."""
    contacts: dict[str, dict[str, str]] = {}

    for e in entities:
        if e.type != "email":
            continue
        for field in ("from", "to"):
            raw = e.properties.get(field, "")
            if not raw:
                continue
            for addr_part in raw.split(","):
                name, email = _parse_email_address(addr_part)
                if not email or "@" not in email:
                    continue
                email_lower = email.lower().strip()
                if email_lower not in contacts:
                    contacts[email_lower] = {"name": name, "email": email_lower}

    people: list[EntityRecord] = []
    for email_lower, info in contacts.items():
        # Skip noreply/system addresses
        if any(
            skip in email_lower
            for skip in [
                "noreply",
                "no-reply",
                "mailer-daemon",
                "notifications",
                "donotreply",
                "system",
                "automated",
            ]
        ):
            continue

        display_name = info["name"]
        if not display_name or display_name == email_lower:
            display_name = email_lower.split("@")[0].replace(".", " ").title()

        people.append(
            EntityRecord(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"person:{email_lower}")),
                type="person",
                name=display_name,
                source="google-mail",
                source_id=email_lower,
                properties={"email": email_lower},
                fetched_at=datetime.utcnow().isoformat(),
                connection_id=connection_id,
            )
        )

    return people


def _extract_companies_from_people(
    people: list[EntityRecord], connection_id: str
) -> list[EntityRecord]:
    """Extract unique companies from email domains."""
    domains: dict[str, int] = {}
    SKIP_DOMAINS = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "aol.com",
        "icloud.com",
        "me.com",
        "mail.com",
        "protonmail.com",
        "googlemail.com",
    }

    for p in people:
        email = p.properties.get("email", "")
        if "@" not in email:
            continue
        domain = email.split("@")[1].lower()
        if domain not in SKIP_DOMAINS:
            domains[domain] = domains.get(domain, 0) + 1

    companies: list[EntityRecord] = []
    for domain, contact_count in domains.items():
        company_name = domain.split(".")[0].title()
        companies.append(
            EntityRecord(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"company:{domain}")),
                type="company",
                name=company_name,
                source="google-mail",
                source_id=domain,
                properties={
                    "domain": domain,
                    "contact_count": contact_count,
                },
                fetched_at=datetime.utcnow().isoformat(),
                connection_id=connection_id,
            )
        )

    return companies


async def _ingest_gmail(
    secret: str, connection_id: str, limit: int
) -> tuple[list[EntityRecord], list[str]]:
    """Fetch recent emails via Gmail API through Nango proxy."""
    entities: list[EntityRecord] = []
    errors: list[str] = []

    data = await _nango_proxy_get(
        secret,
        connection_id,
        "google-mail",
        "gmail/v1/users/me/messages",
        {"maxResults": str(limit)},
    )

    if not data or "messages" not in data:
        errors.append("No messages returned from Gmail")
        return entities, errors

    messages = data.get("messages", [])[:limit]

    for msg_stub in messages:
        msg_id = msg_stub.get("id", "")
        detail = await _nango_proxy_get(
            secret,
            connection_id,
            "google-mail",
            f"gmail/v1/users/me/messages/{msg_id}",
            {"format": "full"},
        )
        if not detail:
            continue

        headers = {}
        for h in detail.get("payload", {}).get("headers", []):
            hname = h.get("name", "").lower()
            hval = h.get("value", "")
            if hname in ("subject", "from", "to", "date", "cc"):
                headers[hname] = hval

        subject = headers.get("subject", "")
        from_addr = headers.get("from", "unknown")
        to_addr = headers.get("to", "")
        date = headers.get("date", "")
        snippet = detail.get("snippet", "")

        if not subject or subject.strip() == "":
            if snippet:
                subject = snippet[:80] + ("..." if len(snippet) > 80 else "")
            else:
                name, _ = _parse_email_address(from_addr)
                subject = f"Email from {name}"

        entity = EntityRecord(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"gmail:{msg_id}")),
            type="email",
            name=subject,
            source="google-mail",
            source_id=msg_id,
            properties={
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "snippet": snippet[:300],
                "labels": ", ".join(detail.get("labelIds", [])),
            },
            fetched_at=datetime.utcnow().isoformat(),
            connection_id=connection_id,
        )
        entities.append(entity)

    # Extract people and companies from email metadata
    people = _extract_people_from_emails(entities, connection_id)
    companies = _extract_companies_from_people(people, connection_id)
    entities.extend(people)
    entities.extend(companies)

    return entities, errors


async def _ingest_google_drive(
    secret: str, connection_id: str, limit: int
) -> tuple[list[EntityRecord], list[str]]:
    """Fetch recent files via Google Drive API through Nango proxy."""
    entities: list[EntityRecord] = []
    errors: list[str] = []

    data = await _nango_proxy_get(
        secret,
        connection_id,
        "google-drive",
        "drive/v3/files",
        {
            "pageSize": str(limit),
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,mimeType,modifiedTime,owners,size,webViewLink)",
        },
    )

    if not data or "files" not in data:
        errors.append("No files returned from Google Drive")
        return entities, errors

    PARSEABLE_MIMES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/csv",
        "text/plain",
    }

    for f in data.get("files", [])[:limit]:
        owner = ""
        if f.get("owners"):
            owner = f["owners"][0].get(
                "displayName", f["owners"][0].get("emailAddress", "")
            )

        mime = f.get("mimeType", "")
        link = f.get("webViewLink", "")
        props: dict[str, Any] = {
            "mime_type": mime,
            "modified": f.get("modifiedTime", ""),
            "owner": owner,
            "size": f.get("size", ""),
            "link": link,
        }

        # Parse document content via LlamaCloud if parseable
        if mime in PARSEABLE_MIMES and link:
            parsed_text = await _llamacloud_parse(link, f.get("name", "doc"), mime)
            if parsed_text:
                props["parsed_content"] = parsed_text[:5000]
                props["parsed"] = True
                logger.info("document_parsed", name=f.get("name"), chars=len(parsed_text))

        entity = EntityRecord(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"gdrive:{f['id']}")),
            type="document",
            name=f.get("name", "Untitled"),
            source="google-drive",
            source_id=f["id"],
            properties=props,
            fetched_at=datetime.utcnow().isoformat(),
            connection_id=connection_id,
        )
        entities.append(entity)

    return entities, errors


async def _ingest_google_sheets(
    secret: str, connection_id: str, limit: int
) -> tuple[list[EntityRecord], list[str]]:
    """Fetch spreadsheets via Google Drive API (filtered to sheets) through Nango proxy."""
    entities: list[EntityRecord] = []
    errors: list[str] = []

    data = await _nango_proxy_get(
        secret,
        connection_id,
        "google-sheet",
        "drive/v3/files",
        {
            "pageSize": str(limit),
            "q": "mimeType='application/vnd.google-apps.spreadsheet'",
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,modifiedTime,owners,webViewLink)",
        },
    )

    if not data or "files" not in data:
        errors.append("No spreadsheets returned from Google Sheets")
        return entities, errors

    for f in data.get("files", [])[:limit]:
        owner = ""
        if f.get("owners"):
            owner = f["owners"][0].get(
                "displayName", f["owners"][0].get("emailAddress", "")
            )

        entity = EntityRecord(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"gsheet:{f['id']}")),
            type="spreadsheet",
            name=f.get("name", "Untitled"),
            source="google-sheet",
            source_id=f["id"],
            properties={
                "modified": f.get("modifiedTime", ""),
                "owner": owner,
                "link": f.get("webViewLink", ""),
            },
            fetched_at=datetime.utcnow().isoformat(),
            connection_id=connection_id,
        )
        entities.append(entity)

    return entities, errors


async def _hubspot_api_get(
    token: str, endpoint: str, params: dict[str, str] | None = None
) -> dict | None:
    """Call HubSpot API directly with a Private App access token."""
    url = f"https://api.hubapi.com/{endpoint}"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("hubspot_api_error", status=resp.status_code, body=resp.text[:200])
        except Exception as e:
            logger.warning("hubspot_api_exception", error=str(e))
    return None


async def _ingest_hubspot(
    secret: str, connection_id: str, limit: int
) -> tuple[list[EntityRecord], list[str]]:
    """Fetch contacts, deals, and companies from HubSpot using Private App token."""
    entities: list[EntityRecord] = []
    errors: list[str] = []

    # Use the Private App token directly (not Nango)
    settings = get_settings()
    token = settings.hubspot_access_token.get_secret_value()
    if not token:
        errors.append("HUBSPOT_ACCESS_TOKEN not configured in .env")
        return entities, errors

    # Fetch contacts
    contacts_data = await _hubspot_api_get(
        token,
        "crm/v3/objects/contacts",
        {"limit": str(min(limit, 100)), "properties": "firstname,lastname,email,company,phone,jobtitle"},
    )

    if contacts_data and "results" in contacts_data:
        for c in contacts_data["results"][:limit]:
            props = c.get("properties", {})
            first = props.get("firstname") or ""
            last = props.get("lastname") or ""
            name = f"{first} {last}".strip() or props.get("email", "Unknown")

            entities.append(
                EntityRecord(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"hubspot:contact:{c['id']}")),
                    type="person",
                    name=name,
                    source="hubspot",
                    source_id=c["id"],
                    properties={
                        "email": props.get("email", ""),
                        "company": props.get("company", ""),
                        "phone": props.get("phone", ""),
                        "job_title": props.get("jobtitle", ""),
                    },
                    fetched_at=datetime.utcnow().isoformat(),
                    connection_id=connection_id or "hubspot-direct",
                )
            )
    else:
        errors.append("No contacts returned from HubSpot")

    # Fetch deals
    deals_data = await _hubspot_api_get(
        token,
        "crm/v3/objects/deals",
        {"limit": str(min(limit, 100)), "properties": "dealname,amount,dealstage,closedate,pipeline"},
    )

    if deals_data and "results" in deals_data:
        for d in deals_data["results"][:limit]:
            props = d.get("properties", {})
            entities.append(
                EntityRecord(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"hubspot:deal:{d['id']}")),
                    type="deal",
                    name=props.get("dealname", f"Deal {d['id']}"),
                    source="hubspot",
                    source_id=d["id"],
                    properties={
                        "amount": props.get("amount", ""),
                        "stage": props.get("dealstage", ""),
                        "close_date": props.get("closedate", ""),
                        "pipeline": props.get("pipeline", ""),
                    },
                    fetched_at=datetime.utcnow().isoformat(),
                    connection_id=connection_id or "hubspot-direct",
                )
            )

    # Fetch companies
    companies_data = await _hubspot_api_get(
        token,
        "crm/v3/objects/companies",
        {"limit": str(min(limit, 50)), "properties": "name,domain,industry,numberofemployees,city,state"},
    )

    if companies_data and "results" in companies_data:
        for co in companies_data["results"][:limit]:
            props = co.get("properties", {})
            entities.append(
                EntityRecord(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"hubspot:company:{co['id']}")),
                    type="company",
                    name=props.get("name") or f"Company {co['id']}",
                    source="hubspot",
                    source_id=co["id"],
                    properties={
                        "domain": props.get("domain", ""),
                        "industry": props.get("industry", ""),
                        "employees": props.get("numberofemployees", ""),
                        "city": props.get("city", ""),
                        "state": props.get("state", ""),
                    },
                    fetched_at=datetime.utcnow().isoformat(),
                    connection_id=connection_id or "hubspot-direct",
                )
            )

    if not entities:
        errors.append("No HubSpot data returned")

    logger.info("hubspot_ingest_done", contacts=len([e for e in entities if e.type == "person"]),
                deals=len([e for e in entities if e.type == "deal"]),
                companies=len([e for e in entities if e.type == "company"]))

    return entities, errors


PROVIDER_INGESTORS = {
    "google-mail": _ingest_gmail,
    "google-drive": _ingest_google_drive,
    "google-sheet": _ingest_google_sheets,
    "hubspot": _ingest_hubspot,
}


@router.delete("/ingest/clear")
async def clear_entity_store() -> dict:
    """Clear all ingested data (for re-ingestion)."""
    count = len(_entity_store)
    _entity_store.clear()
    _persist_entity_store()
    return {"cleared": count}


@router.post("/ingest/all")
async def ingest_all_connections() -> list[IngestResult]:
    """Trigger ingestion from ALL connected Nango sources."""
    settings = get_settings()
    secret = settings.nango_secret_key.get_secret_value()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.nango.dev/connections",
                headers={"Authorization": f"Bearer {secret}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            connections = (
                data.get("connections", []) if isinstance(data, dict) else data
            )
    except Exception:
        return []

    # Deduplicate connections by provider
    seen: dict[str, dict] = {}
    for conn in connections:
        provider = conn.get(
            "provider_config_key", conn.get("provider", "unknown")
        )
        seen[provider] = conn

    results: list[IngestResult] = []
    for provider, conn in seen.items():
        cid = conn.get("connection_id", "")
        if cid:
            result = await _do_ingest(cid, provider_hint=provider)
            results.append(result)

    # Also ingest HubSpot if token is configured (direct, not via Nango)
    hs_token = settings.hubspot_access_token.get_secret_value()
    if hs_token:
        hs_result = await ingest_hubspot_direct()
        results.append(hs_result)

    return results


@router.post("/ingest/hubspot", response_model=IngestResult)
async def ingest_hubspot_direct() -> IngestResult:
    """Ingest data directly from HubSpot using the Private App token."""
    settings = get_settings()
    token = settings.hubspot_access_token.get_secret_value()

    if not token:
        return IngestResult(
            connection_id="hubspot-direct",
            provider_type="hubspot",
            records_fetched=0,
            entities_created=0,
            errors=["HUBSPOT_ACCESS_TOKEN not set in .env"],
        )

    limit = settings.fast_path_default_n
    entities, errors = await _ingest_hubspot("", "hubspot-direct", limit)

    existing_ids = {(e.source, e.source_id) for e in _entity_store}
    new_count = 0
    for entity in entities:
        if (entity.source, entity.source_id) not in existing_ids:
            _entity_store.append(entity)
            existing_ids.add((entity.source, entity.source_id))
            new_count += 1

    if new_count > 0:
        _persist_entity_store()

    # Auto-generate canon proposals for HubSpot data
    try:
        from services.api.routes.canon import (
            _proposals,
            _assertions,
            Proposal,
            ProposalSource,
            StakeLevel,
            AssertionStatus,
            _persist_proposals,
        )

        proposals_added = False
        for entity in entities:
            already_exists = any(
                (p.entity_name.lower() == entity.name.lower())
                for p in _proposals
            ) or any(
                (a.entity_name.lower() == entity.name.lower()
                 and a.status == AssertionStatus.ACTIVE)
                for a in _assertions
            )
            if already_exists:
                continue

            if entity.type == "company" and entity.properties.get("domain"):
                _proposals.append(Proposal(
                    action="create", entity_name=entity.name,
                    entity_type="company", field="domain",
                    new_value=entity.properties["domain"],
                    source="hubspot", proposed_by="system",
                    proposal_source=ProposalSource.SYSTEM,
                    stake_level=StakeLevel.LOW,
                    reason=f"Company from HubSpot CRM",
                ))
                proposals_added = True
            elif entity.type == "deal" and entity.properties.get("amount"):
                _proposals.append(Proposal(
                    action="create", entity_name=entity.name,
                    entity_type="deal", field="deal_value",
                    new_value=entity.properties["amount"],
                    source="hubspot", proposed_by="system",
                    proposal_source=ProposalSource.SYSTEM,
                    stake_level=StakeLevel.MEDIUM,
                    reason=f"Deal from HubSpot CRM",
                ))
                proposals_added = True
            elif entity.type == "person" and entity.properties.get("company"):
                _proposals.append(Proposal(
                    action="create", entity_name=entity.name,
                    entity_type="person", field="company",
                    new_value=entity.properties["company"],
                    source="hubspot", proposed_by="system",
                    proposal_source=ProposalSource.SYSTEM,
                    stake_level=StakeLevel.LOW,
                    reason=f"Contact from HubSpot CRM",
                ))
                proposals_added = True

        if proposals_added:
            _persist_proposals()
    except Exception as e:
        logger.warning("hubspot_proposal_failed", error=str(e))

    return IngestResult(
        connection_id="hubspot-direct",
        provider_type="hubspot",
        records_fetched=len(entities),
        entities_created=new_count,
        errors=errors,
    )


@router.post("/ingest/{connection_id}", response_model=IngestResult)
async def ingest_from_connection(connection_id: str) -> IngestResult:
    return await _do_ingest(connection_id)


async def _do_ingest(
    connection_id: str, provider_hint: str = ""
) -> IngestResult:
    """Core ingestion logic for a single connection."""
    settings = get_settings()
    secret = settings.nango_secret_key.get_secret_value()
    limit = settings.fast_path_default_n

    provider_type = provider_hint or "unknown"
    if provider_type == "unknown":
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.nango.dev/connections",
                    headers={"Authorization": f"Bearer {secret}"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for conn in data.get("connections", []):
                        if conn.get("connection_id") == connection_id:
                            provider_type = conn.get(
                                "provider_config_key",
                                conn.get("provider", "unknown"),
                            )
                            break
        except Exception as e:
            logger.error(
                "ingest_connection_lookup_failed", error=str(e)
            )

    ingestor = PROVIDER_INGESTORS.get(provider_type)
    if not ingestor:
        return IngestResult(
            connection_id=connection_id,
            provider_type=provider_type,
            records_fetched=0,
            entities_created=0,
            errors=[f"No ingestor for provider: {provider_type}"],
        )

    entities, errors = await ingestor(secret, connection_id, limit)

    existing_ids = {(e.source, e.source_id) for e in _entity_store}
    new_count = 0
    for entity in entities:
        if (entity.source, entity.source_id) not in existing_ids:
            _entity_store.append(entity)
            existing_ids.add((entity.source, entity.source_id))
            new_count += 1

    if new_count > 0:
        _persist_entity_store()

    # Auto-generate canon proposals from meaningful ingested data.
    # Rules:
    #  - CRM sources (HubSpot): always propose companies, deals, contacts
    #  - Email sources: only propose companies with 2+ contacts (real business relationships)
    #  - Never propose SaaS notification senders or generic domains
    SAAS_DOMAINS = {
        "google.com", "github.com", "nango.dev", "airbyte.io", "temporal.io",
        "grafana.com", "llamaindex.ai", "qdrant.com", "hubspot.com",
        "redpanda.com", "fireflies.ai", "cloud.google.com",
        "accounts.google.com", "bcc.na2.hubspot.com",
    }
    CRM_SOURCES = {"hubspot", "salesforce", "pipedrive"}

    try:
        from services.api.routes.canon import (
            _proposals,
            _assertions,
            Proposal,
            ProposalSource,
            StakeLevel,
            AssertionStatus,
            _persist_proposals,
        )

        proposals_added = False

        for entity in entities:
            # Skip if already proposed or asserted
            already_exists = any(
                (p.entity_name.lower() == entity.name.lower() and p.field != "")
                for p in _proposals
            ) or any(
                (a.entity_name.lower() == entity.name.lower()
                 and a.status == AssertionStatus.ACTIVE)
                for a in _assertions
            )
            if already_exists:
                continue

            # --- CRM sources: propose everything meaningful ---
            if entity.source in CRM_SOURCES:
                if entity.type == "company" and entity.properties.get("domain"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="company", field="domain",
                        new_value=entity.properties["domain"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.LOW,
                        reason=f"Company from {entity.source} CRM",
                    ))
                    proposals_added = True

                    if entity.properties.get("industry"):
                        _proposals.append(Proposal(
                            action="create", entity_name=entity.name,
                            entity_type="company", field="industry",
                            new_value=entity.properties["industry"],
                            source=entity.source, proposed_by="system",
                            proposal_source=ProposalSource.SYSTEM,
                            stake_level=StakeLevel.LOW,
                            reason=f"Company from {entity.source} CRM",
                        ))

                elif entity.type == "deal" and entity.properties.get("amount"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="deal", field="deal_value",
                        new_value=entity.properties["amount"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.MEDIUM,
                        reason=f"Deal from {entity.source} CRM",
                    ))
                    proposals_added = True

                elif entity.type == "person" and entity.properties.get("company"):
                    _proposals.append(Proposal(
                        action="create", entity_name=entity.name,
                        entity_type="person", field="company",
                        new_value=entity.properties["company"],
                        source=entity.source, proposed_by="system",
                        proposal_source=ProposalSource.SYSTEM,
                        stake_level=StakeLevel.LOW,
                        reason=f"Contact from {entity.source} CRM",
                    ))
                    proposals_added = True

            # --- Email sources: only propose companies with real business signal ---
            elif entity.source == "google-mail" and entity.type == "company":
                domain = entity.properties.get("domain", "")
                contact_count = int(entity.properties.get("contact_count", 0))

                # Skip SaaS/service domains
                if domain in SAAS_DOMAINS:
                    continue

                _proposals.append(Proposal(
                    action="create", entity_name=entity.name,
                    entity_type="company", field="domain",
                    new_value=domain,
                    source="google-mail", proposed_by="system",
                    proposal_source=ProposalSource.SYSTEM,
                    stake_level=StakeLevel.LOW,
                    reason=f"Company with {contact_count} contacts in your email",
                ))
                proposals_added = True

        if proposals_added:
            _persist_proposals()
    except Exception as e:
        if "skip" not in str(e):
            logger.warning("canon_proposal_generation_failed", error=str(e))

    logger.info(
        "ingest_complete",
        connection_id=connection_id,
        provider=provider_type,
        fetched=len(entities),
        new_entities=new_count,
    )

    return IngestResult(
        connection_id=connection_id,
        provider_type=provider_type,
        records_fetched=len(entities),
        entities_created=new_count,
        errors=errors,
    )
