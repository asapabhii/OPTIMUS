"""Connector registration — specialized connectors auto-register on import."""

from connectors.registry import register_specialized
from connectors.specialized.google_sheets import GoogleSheetsConnector
from connectors.specialized.hubspot import HubSpotConnector
from connectors.specialized.gmail import GmailConnector

# Register specialized connectors
register_specialized("google_sheets", GoogleSheetsConnector)
register_specialized("hubspot", HubSpotConnector)
register_specialized("gmail", GmailConnector)
