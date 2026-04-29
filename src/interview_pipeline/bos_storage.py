from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .config import BosSettings


@dataclass
class BosUploadResult:
    object_key: str
    signed_url: str
    public_url: str


class BosStorageClient:
    def __init__(self, settings: BosSettings) -> None:
        self._settings = settings
        self._sdk = _load_bos_sdk()
        self._client = self._build_client()

    def upload_file(self, file_path: str | Path, *, object_key: str | None = None) -> BosUploadResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"BOS upload source file not found: {path}")

        key = object_key or self._default_object_key(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        file_size = path.stat().st_size

        try:
            with _proxy_override(self._settings.disable_proxy):
                if file_size >= self._settings.multipart_threshold_bytes:
                    # Use the SDK's multipart path for larger audio files so we
                    # are not blocked on a single long-running PUT.
                    ok = self._client.put_super_object_from_file(
                        self._settings.bucket,
                        key,
                        str(path),
                        chunk_size=self._settings.multipart_chunk_size_mb,
                        content_type=content_type,
                    )
                    if not ok:
                        raise RuntimeError("BOS multipart upload did not complete successfully.")
                else:
                    data = path.read_bytes()
                    self._client.put_object_from_string(
                        self._settings.bucket,
                        key,
                        data,
                        content_type=content_type,
                    )
                signed_url = self._decode_url(
                    self._client.generate_pre_signed_url(
                        self._settings.bucket,
                        key,
                        expiration_in_seconds=self._settings.signed_url_expiration_seconds,
                    )
                )
        except Exception as exc:  # pragma: no cover - SDK-specific exceptions vary by version.
            raise RuntimeError(f"Failed to upload file to BOS via official SDK: {exc}") from exc

        return BosUploadResult(
            object_key=key,
            signed_url=signed_url,
            public_url=_build_public_url(self._settings.bucket, self._settings.endpoint, key),
        )

    def generate_signed_url(self, object_key: str, *, expires_in: int | None = None) -> str:
        expiration = self._settings.signed_url_expiration_seconds if expires_in is None else expires_in
        try:
            with _proxy_override(self._settings.disable_proxy):
                return self._decode_url(
                    self._client.generate_pre_signed_url(
                        self._settings.bucket,
                        object_key,
                        expiration_in_seconds=expiration,
                    )
                )
        except Exception as exc:  # pragma: no cover - SDK-specific exceptions vary by version.
            raise RuntimeError(f"Failed to generate BOS signed URL via official SDK: {exc}") from exc

    def _build_client(self):
        credentials = self._sdk["BceCredentials"](
            self._settings.access_key_id,
            self._settings.secret_access_key,
        )
        configuration = self._sdk["BceClientConfiguration"](
            credentials=credentials,
            endpoint=self._settings.endpoint.encode("utf-8"),
            protocol=self._sdk["protocol"].HTTPS,
            path_style_enable=False,
        )
        return self._sdk["BosClient"](configuration)

    def _decode_url(self, value: str | bytes) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def _default_object_key(self, path: Path) -> str:
        now = datetime.now(timezone.utc)
        digest = hashlib.sha1(f"{path.name}:{path.stat().st_size}:{now.timestamp()}".encode("utf-8")).hexdigest()[:12]
        prefix = self._settings.object_prefix.strip("/").replace("\\", "/")
        date_prefix = now.strftime("%Y/%m/%d")
        safe_name = _normalize_object_name(path.name)
        return f"{prefix}/{date_prefix}/{digest}_{safe_name}"


def _normalize_object_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in name)


def _build_public_url(bucket: str, endpoint: str, object_key: str) -> str:
    quoted_key = quote(object_key.strip("/"), safe="/._-~")
    host = endpoint.removeprefix("https://").removeprefix("http://").strip("/")
    return f"https://{bucket}.{host}/{quoted_key}"


def _load_bos_sdk() -> dict[str, object]:
    try:
        from baidubce import protocol
        from baidubce.auth.bce_credentials import BceCredentials
        from baidubce.bce_client_configuration import BceClientConfiguration
        from baidubce.services.bos.bos_client import BosClient
    except ModuleNotFoundError:
        vendor_dir = Path(__file__).resolve().parents[2] / ".vendor"
        if vendor_dir.exists():
            sys.path.insert(0, str(vendor_dir))
        try:
            from baidubce import protocol
            from baidubce.auth.bce_credentials import BceCredentials
            from baidubce.bce_client_configuration import BceClientConfiguration
            from baidubce.services.bos.bos_client import BosClient
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing BOS SDK dependency. Install `bce-python-sdk` or make sure `.vendor` contains it."
            ) from exc

    return {
        "protocol": protocol,
        "BceCredentials": BceCredentials,
        "BceClientConfiguration": BceClientConfiguration,
        "BosClient": BosClient,
    }


@contextmanager
def _proxy_override(disable_proxy: bool):
    if not disable_proxy:
        yield
        return

    proxy_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
        "all_proxy",
    ]
    original = {key: os.environ.get(key) for key in proxy_keys}
    try:
        for key in proxy_keys:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
