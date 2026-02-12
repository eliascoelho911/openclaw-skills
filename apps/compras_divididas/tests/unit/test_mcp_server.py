from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from fastmcp import Client

from compras_divididas.mcp.server import _build_api_error, create_mcp_server


@dataclass
class FakeRequester:
    responses: dict[tuple[str, str], object]
    calls: list[dict[str, object]] = field(default_factory=list)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> object:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": dict(params) if params else None,
                "json_body": dict(json_body) if json_body else None,
            }
        )

        value = self.responses[(method, path)]
        if isinstance(value, Exception):
            raise value
        return value


def test_create_mcp_server_registers_expected_tools() -> None:
    async def scenario() -> list[str]:
        fake_requester = FakeRequester(responses={("GET", "/v1/participants"): {}})
        server = create_mcp_server(
            api_base_url="http://example.test",
            timeout_seconds=1,
            requester=fake_requester,
        )
        async with Client(server) as client:
            tools = await client.list_tools()
        return sorted(tool.name for tool in tools)

    tool_names = asyncio.run(scenario())

    assert tool_names == [
        "create_movement",
        "get_monthly_report",
        "get_monthly_summary",
        "list_movements",
        "list_participants",
    ]


def test_list_participants_tool_returns_api_payload() -> None:
    expected_payload: dict[str, Any] = {
        "participants": [
            {"id": "ana", "display_name": "Ana", "is_active": True},
            {"id": "bia", "display_name": "Bia", "is_active": True},
        ]
    }

    async def scenario() -> object:
        fake_requester = FakeRequester(
            responses={("GET", "/v1/participants"): expected_payload}
        )
        server = create_mcp_server(
            api_base_url="http://example.test",
            timeout_seconds=1,
            requester=fake_requester,
        )
        async with Client(server) as client:
            result = await client.call_tool("list_participants", {})
        return result.data

    tool_result = asyncio.run(scenario())
    assert tool_result == expected_payload


def test_create_movement_tool_sends_expected_payload() -> None:
    async def scenario() -> dict[str, object]:
        fake_requester = FakeRequester(
            responses={("POST", "/v1/movements"): {"id": "123"}}
        )
        server = create_mcp_server(
            api_base_url="http://example.test",
            timeout_seconds=1,
            requester=fake_requester,
        )
        async with Client(server) as client:
            await client.call_tool(
                "create_movement",
                {
                    "type": "purchase",
                    "amount": "10.00",
                    "description": "Padaria",
                    "requested_by_participant_id": "ana",
                    "external_id": "msg-001",
                },
            )
        return fake_requester.calls[0]

    recorded_call = asyncio.run(scenario())

    assert recorded_call == {
        "method": "POST",
        "path": "/v1/movements",
        "params": None,
        "json_body": {
            "type": "purchase",
            "amount": "10.00",
            "description": "Padaria",
            "requested_by_participant_id": "ana",
            "external_id": "msg-001",
        },
    }


def test_create_mcp_server_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        create_mcp_server(api_base_url="http://example.test", timeout_seconds=0)


def test_build_api_error_uses_contract_payload_shape() -> None:
    response = httpx.Response(
        status_code=409,
        json={
            "code": "DUPLICATE_EXTERNAL_ID",
            "message": "Cause: duplicate. Action: use a unique id.",
            "details": {"external_id": "msg-001"},
        },
        request=httpx.Request("POST", "http://example.test/v1/movements"),
    )

    error_message = _build_api_error(response)

    assert "DUPLICATE_EXTERNAL_ID" in error_message
    assert "details={'external_id': 'msg-001'}" in error_message


def test_get_monthly_summary_tool_forwards_auto_generate() -> None:
    async def scenario() -> dict[str, object]:
        fake_requester = FakeRequester(
            responses={("GET", "/v1/months/2026/2/summary"): {"ok": True}}
        )
        server = create_mcp_server(
            api_base_url="http://example.test",
            timeout_seconds=1,
            requester=fake_requester,
        )
        async with Client(server) as client:
            await client.call_tool(
                "get_monthly_summary",
                {"year": 2026, "month": 2, "auto_generate": True},
            )
        return fake_requester.calls[0]

    recorded_call = asyncio.run(scenario())

    assert recorded_call == {
        "method": "GET",
        "path": "/v1/months/2026/2/summary",
        "params": {"auto_generate": True},
        "json_body": None,
    }


def test_get_monthly_report_tool_forwards_auto_generate() -> None:
    async def scenario() -> dict[str, object]:
        fake_requester = FakeRequester(
            responses={("GET", "/v1/months/2026/2/report"): {"ok": True}}
        )
        server = create_mcp_server(
            api_base_url="http://example.test",
            timeout_seconds=1,
            requester=fake_requester,
        )
        async with Client(server) as client:
            await client.call_tool(
                "get_monthly_report",
                {"year": 2026, "month": 2, "auto_generate": True},
            )
        return fake_requester.calls[0]

    recorded_call = asyncio.run(scenario())

    assert recorded_call == {
        "method": "GET",
        "path": "/v1/months/2026/2/report",
        "params": {"auto_generate": True},
        "json_body": None,
    }
