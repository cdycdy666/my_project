from __future__ import annotations

import json
import itertools
from dataclasses import dataclass
from typing import Any

from .http import HttpClient


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]


class StreamableHttpMcpClient:
    def __init__(
        self,
        url: str,
        bearer_token: str,
        protocol_version: str,
        *,
        disable_proxy: bool = False,
    ) -> None:
        self._url = url
        self._protocol_version = protocol_version
        self._http = HttpClient()
        self._bearer_token = bearer_token
        self._disable_proxy = disable_proxy
        self._session_id: str | None = None
        self._request_ids = itertools.count(1)
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        response = self._send_request(
            method="initialize",
            params={
                "protocolVersion": self._protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "interview-audio-pipeline",
                    "version": "0.1.0",
                },
            },
        )
        server_protocol = response.get("result", {}).get("protocolVersion")
        if server_protocol:
            self._protocol_version = server_protocol

        self._send_notification("notifications/initialized")
        self._initialized = True

    def list_tools(self) -> list[McpTool]:
        self.initialize()
        response = self._send_request("tools/list", {})
        tools = response.get("result", {}).get("tools", [])
        return [
            McpTool(
                name=item["name"],
                description=item.get("description", ""),
                input_schema=item.get("inputSchema", {}),
            )
            for item in tools
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        response = self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
            mcp_name=name,
        )
        result = response.get("result", {})
        return _coerce_tool_result(result)

    def _send_notification(self, method: str) -> None:
        self._post(
            payload={"jsonrpc": "2.0", "method": method},
            method=method,
            expect_response=False,
        )

    def _send_request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        mcp_name: str | None = None,
    ) -> dict[str, Any]:
        request_id = next(self._request_ids)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        body = self._post(payload=payload, method=method, mcp_name=mcp_name, expect_response=True)
        response = _parse_transport_response(body, request_id)
        if "error" in response:
            raise RuntimeError(f"MCP error for {method}: {response['error']}")
        return response

    def _post(
        self,
        *,
        payload: dict[str, Any],
        method: str,
        expect_response: bool,
        mcp_name: str | None = None,
    ) -> bytes:
        headers = {
            "Authorization": f"Bearer {self._bearer_token}",
            "Accept": "application/json, text/event-stream",
            "Mcp-Method": method,
            "MCP-Protocol-Version": self._protocol_version,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        if mcp_name:
            headers["Mcp-Name"] = mcp_name

        status, response_headers, body = self._http.request(
            "POST",
            self._url,
            headers=headers,
            json_body=payload,
            disable_proxy=self._disable_proxy,
        )
        if not self._session_id:
            self._session_id = response_headers.get("Mcp-Session-Id") or response_headers.get(
                "MCP-Session-Id"
            )

        if not expect_response and status == 202:
            return b""
        if status >= 400:
            raise RuntimeError(
                f"MCP HTTP error {status}: {body.decode('utf-8', errors='replace')}"
            )
        return body


def _parse_transport_response(body: bytes, request_id: int) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        raise RuntimeError("Empty MCP response body")

    if text.startswith("{") or text.startswith("["):
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                if item.get("id") == request_id:
                    return item
            raise RuntimeError(f"Could not find JSON-RPC response for request id {request_id}")
        return parsed

    messages: list[dict[str, Any]] = []
    event_data: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if event_data:
                messages.extend(_decode_sse_event_data(event_data))
                event_data = []
            continue
        if line.startswith("data:"):
            event_data.append(line[5:].lstrip())
    if event_data:
        messages.extend(_decode_sse_event_data(event_data))

    for message in messages:
        if message.get("id") == request_id:
            return message
    raise RuntimeError(f"Could not find JSON-RPC response in SSE payload for request id {request_id}")


def _decode_sse_event_data(lines: list[str]) -> list[dict[str, Any]]:
    payload = "\n".join(lines).strip()
    if not payload:
        return []
    parsed = json.loads(payload)
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _coerce_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    content = result.get("content", [])
    extracted: dict[str, Any] = {}
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "").strip()
            if not text:
                continue
            try:
                candidate = json.loads(text)
            except json.JSONDecodeError:
                extracted.setdefault("text", [])
                extracted["text"].append(text)
                continue
            if isinstance(candidate, dict):
                extracted.update(candidate)
        elif item.get("type") == "json":
            candidate = item.get("json")
            if isinstance(candidate, dict):
                extracted.update(candidate)

    if extracted:
        return extracted
    return result
