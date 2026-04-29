from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener, urlopen


class HttpClient:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        raw_body: bytes | None = None,
        disable_proxy: bool = False,
        timeout: int = 60,
    ) -> tuple[int, dict[str, str], bytes]:
        body = raw_body
        final_headers = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            final_headers.setdefault("Content-Type", "application/json")

        request = Request(url=url, method=method.upper(), data=body, headers=final_headers)
        try:
            opener = build_opener(ProxyHandler({})) if disable_proxy else None
            open_fn = opener.open if opener else urlopen
            with open_fn(request, timeout=timeout) as response:
                payload = response.read()
                return response.status, dict(response.headers.items()), payload
        except HTTPError as exc:
            payload = exc.read()
            return exc.code, dict(exc.headers.items()), payload
        except URLError as exc:
            raise RuntimeError(f"Network request failed for {url}: {exc}") from exc
