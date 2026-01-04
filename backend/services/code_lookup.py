"""HCPCS code lookup service (placeholder - main logic in router)."""
from typing import Optional


def get_code_info(code: str) -> Optional[dict]:
    """Get info for a specific code - delegated to router."""
    pass


def search_codes(query: str, category: Optional[str] = None) -> list[dict]:
    """Search codes - delegated to router."""
    pass
