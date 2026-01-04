"""Verity API client for Medicare coverage intelligence."""
import httpx
from typing import Optional
from config import get_settings

VERITY_BASE_URL = "https://verity.backworkai.com/api/v1"


class VerityClient:
    """Client for Verity Healthcare API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_settings().verity_api_key
        self.base_url = VERITY_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make async request to Verity API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            data = response.json()
            if not data.get("success", False):
                error = data.get("error", {})
                raise VerityAPIError(
                    error.get("message", "Unknown error"),
                    error.get("code", "UNKNOWN"),
                )
            return data.get("data", {})

    async def lookup_code(
        self,
        code: str,
        include_policies: bool = True,
        include_rvu: bool = True,
    ) -> dict:
        """
        Look up HCPCS/CPT/ICD-10 code with coverage policies.

        Args:
            code: The medical code (e.g., "A9276")
            include_policies: Include related coverage policies
            include_rvu: Include RVU pricing data

        Returns:
            Code details with policies and pricing
        """
        includes = []
        if include_policies:
            includes.append("policies")
        if include_rvu:
            includes.append("rvu")

        params = {"code": code}
        if includes:
            params["include"] = ",".join(includes)

        return await self._request("GET", "/codes/lookup", params=params)

    async def search_policies(
        self,
        query: str,
        policy_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        Search Medicare coverage policies.

        Args:
            query: Search term (e.g., "CGM", "glucose monitor")
            policy_type: Filter by type (LCD, NCD, Article)
            jurisdiction: Filter by MAC jurisdiction (e.g., "JM", "JH")
            limit: Max results to return

        Returns:
            List of matching policies
        """
        params = {"query": query, "limit": limit}
        if policy_type:
            params["policy_type"] = policy_type
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        return await self._request("GET", "/policies/search", params=params)

    async def get_policy(
        self,
        policy_id: str,
        include_criteria: bool = True,
        include_codes: bool = True,
    ) -> dict:
        """
        Get detailed policy information.

        Args:
            policy_id: Policy ID (e.g., "L33822")
            include_criteria: Include coverage criteria
            include_codes: Include covered codes

        Returns:
            Full policy details
        """
        includes = []
        if include_criteria:
            includes.append("criteria")
        if include_codes:
            includes.append("codes")

        params = {}
        if includes:
            params["include"] = ",".join(includes)

        return await self._request("GET", f"/policies/{policy_id}", params=params)

    async def check_prior_auth(
        self,
        procedure_codes: list[str],
        state: Optional[str] = None,
        diagnosis_codes: Optional[list[str]] = None,
    ) -> dict:
        """
        Check if prior authorization is required.

        Args:
            procedure_codes: List of CPT/HCPCS codes
            state: Two-letter state code for MAC jurisdiction
            diagnosis_codes: Optional ICD-10 diagnosis codes

        Returns:
            Prior auth requirements and documentation checklist
        """
        payload = {"procedure_codes": procedure_codes}
        if state:
            payload["state"] = state
        if diagnosis_codes:
            payload["diagnosis_codes"] = diagnosis_codes

        return await self._request("POST", "/prior-auth/check", json=payload)

    async def list_jurisdictions(self) -> dict:
        """Get list of MAC jurisdictions and covered states."""
        return await self._request("GET", "/jurisdictions")

    async def compare_policies(
        self,
        procedure_codes: list[str],
        jurisdictions: Optional[list[str]] = None,
    ) -> dict:
        """
        Compare coverage across jurisdictions.

        Args:
            procedure_codes: Codes to compare
            jurisdictions: Specific MACs to compare (optional)

        Returns:
            Coverage comparison across MACs
        """
        params = {"procedure_codes": ",".join(procedure_codes)}
        if jurisdictions:
            params["jurisdictions"] = ",".join(jurisdictions)

        return await self._request("GET", "/policies/compare", params=params)

    async def get_policy_changes(
        self,
        since: Optional[str] = None,
        policy_id: Optional[str] = None,
        change_type: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        Track recent changes to Medicare coverage policies.

        Args:
            since: ISO8601 timestamp - only changes after this date
            policy_id: Filter to a specific policy
            change_type: Filter by type (created, updated, retired, codes_changed, criteria_changed)
            limit: Results per page (max 100)

        Returns:
            List of policy changes with details
        """
        params = {"limit": limit}
        if since:
            params["since"] = since
        if policy_id:
            params["policy_id"] = policy_id
        if change_type:
            params["change_type"] = change_type

        return await self._request("GET", "/policies/changes", params=params)


class VerityAPIError(Exception):
    """Exception for Verity API errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(f"{code}: {message}")


# Singleton client instance
_client: Optional[VerityClient] = None


def get_verity_client() -> VerityClient:
    """Get or create Verity client singleton."""
    global _client
    if _client is None:
        _client = VerityClient()
    return _client
