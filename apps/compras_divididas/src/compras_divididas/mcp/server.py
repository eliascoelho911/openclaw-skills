"""MCP server exposing compras_divididas API capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx
from fastmcp import FastMCP

from compras_divididas.core.settings import get_settings

MovementKind = Literal["purchase", "refund"]
MovementFilterKind = Literal["purchase", "refund"]
ParamValue = str | int | float | bool | None
ParamsMapping = Mapping[str, ParamValue]


class APIRequester(Protocol):
    """Requester abstraction to simplify HTTP boundary testing."""

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: ParamsMapping | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> object: ...


@dataclass(slots=True, frozen=True)
class HTTPAPIRequester:
    """HTTP client wrapper for compras_divididas API."""

    base_url: str
    timeout_seconds: float

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: ParamsMapping | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> object:
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                json=dict(json_body) if json_body else None,
            )

        if response.is_success:
            return _parse_json_response(response)
        raise RuntimeError(_build_api_error(response))


def _parse_json_response(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"API returned a non-JSON response with status {response.status_code}."
        ) from exc


def _build_api_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        if text:
            return f"API request failed with status {response.status_code}: {text}"
        return f"API request failed with status {response.status_code}."

    if isinstance(payload, Mapping):
        error_code = payload.get("code")
        error_message = payload.get("message")
        details = payload.get("details")
        if isinstance(error_code, str) and isinstance(error_message, str):
            if details is None:
                return f"API error {error_code}: {error_message}"
            return f"API error {error_code}: {error_message} | details={details}"

    return f"API request failed with status {response.status_code}: {payload}"


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def create_mcp_server(
    *,
    api_base_url: str | None = None,
    timeout_seconds: float | None = None,
    requester: APIRequester | None = None,
) -> FastMCP:
    """Create MCP server with curated tools mapped to REST endpoints."""

    settings = get_settings()
    resolved_base_url = _normalize_base_url(api_base_url or settings.mcp_api_base_url)
    resolved_timeout = (
        settings.mcp_api_timeout_seconds if timeout_seconds is None else timeout_seconds
    )
    if resolved_timeout <= 0:
        raise ValueError("MCP API timeout must be greater than zero.")

    mcp = FastMCP(name="Compras Divididas")
    api_requester: APIRequester = requester or HTTPAPIRequester(
        base_url=resolved_base_url,
        timeout_seconds=resolved_timeout,
    )

    @mcp.tool
    async def list_participants() -> object:
        """List active participants used by reconciliation."""

        return await api_requester.request("GET", "/v1/participants")

    @mcp.tool
    async def list_movements(
        year: int,
        month: int,
        type: MovementFilterKind | None = None,
        description: str | None = None,
        amount: str | None = None,
        participant_id: str | None = None,
        external_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> object:
        """List movements for a month with optional filters."""

        params: dict[str, ParamValue] = {
            "year": year,
            "month": month,
            "limit": limit,
            "offset": offset,
        }
        if type is not None:
            params["type"] = type
        if description is not None:
            params["description"] = description
        if amount is not None:
            params["amount"] = amount
        if participant_id is not None:
            params["participant_id"] = participant_id
        if external_id is not None:
            params["external_id"] = external_id

        return await api_requester.request("GET", "/v1/movements", params=params)

    @mcp.tool
    async def create_movement(
        type: MovementKind,
        amount: str,
        description: str,
        requested_by_participant_id: str,
        occurred_at: str | None = None,
        payer_participant_id: str | None = None,
        external_id: str | None = None,
        original_purchase_id: str | None = None,
        original_purchase_external_id: str | None = None,
    ) -> object:
        """Create a purchase or refund movement."""

        payload: dict[str, object] = {
            "type": type,
            "amount": amount,
            "description": description,
            "requested_by_participant_id": requested_by_participant_id,
        }
        if occurred_at is not None:
            payload["occurred_at"] = occurred_at
        if payer_participant_id is not None:
            payload["payer_participant_id"] = payer_participant_id
        if external_id is not None:
            payload["external_id"] = external_id
        if original_purchase_id is not None:
            payload["original_purchase_id"] = original_purchase_id
        if original_purchase_external_id is not None:
            payload["original_purchase_external_id"] = original_purchase_external_id

        return await api_requester.request(
            "POST",
            "/v1/movements",
            json_body=payload,
        )

    @mcp.tool
    async def get_monthly_summary(year: int, month: int) -> object:
        """Return monthly summary projection for a competence month."""

        return await api_requester.request("GET", f"/v1/months/{year}/{month}/summary")

    @mcp.tool
    async def get_monthly_report(
        year: int,
        month: int,
    ) -> object:
        """Return monthly report projection for a competence month."""

        return await api_requester.request("GET", f"/v1/months/{year}/{month}/report")

    return mcp
