"""Firestore REST client with Service Account JWT authentication."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import jwt

from .const import FIRESTORE_BASE, FIRESTORE_SCOPE

_LOGGER = logging.getLogger(__name__)


def _build_jwt(sa: dict) -> str:
    now = int(time.time())
    payload = {
        "iss": sa["client_email"],
        "scope": FIRESTORE_SCOPE,
        "aud": sa["token_uri"],
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, sa["private_key"], algorithm="RS256")


def parse_fields(doc: dict) -> dict:
    """Convert Firestore typed fields to a flat Python dict."""
    return {key: _parse_value(val) for key, val in doc.get("fields", {}).items()}


def _parse_value(val: dict) -> Any:
    if "stringValue" in val:
        return val["stringValue"]
    if "booleanValue" in val:
        return val["booleanValue"]
    if "integerValue" in val:
        return int(val["integerValue"])
    if "doubleValue" in val:
        return float(val["doubleValue"])
    if "timestampValue" in val:
        return val["timestampValue"]
    if "arrayValue" in val:
        return [_parse_value(v) for v in val["arrayValue"].get("values", [])]
    if "mapValue" in val:
        return {k: _parse_value(v) for k, v in val["mapValue"].get("fields", {}).items()}
    if "nullValue" in val:
        return None
    return None


def to_fields(data: dict) -> dict:
    """Convert a flat Python dict to Firestore typed fields format."""
    return {key: _to_value(val) for key, val in data.items()}


def _to_value(val: Any) -> dict:
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, str):
        return {"stringValue": val}
    if isinstance(val, list):
        return {"arrayValue": {"values": [_to_value(v) for v in val]}}
    if isinstance(val, dict):
        return {"mapValue": {"fields": {k: _to_value(v) for k, v in val.items()}}}
    return {"stringValue": str(val)}


class FirestoreClient:
    def __init__(self, session, sa: dict) -> None:
        self._session = session
        self._sa = sa
        self._access_token: str | None = None
        self._token_expiry: float = 0.0
        self._base = FIRESTORE_BASE.format(project_id=sa["project_id"])

    async def _ensure_token(self) -> None:
        if self._access_token and time.time() < self._token_expiry:
            return
        assertion = _build_jwt(self._sa)
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
        async with self._session.post(self._sa["token_uri"], data=data) as resp:
            resp.raise_for_status()
            body = await resp.json()
        self._access_token = body["access_token"]
        self._token_expiry = time.time() + body["expires_in"] - 60

    async def _headers(self) -> dict:
        await self._ensure_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    async def get_document(self, path: str) -> dict:
        """Read a single document; returns parsed fields dict."""
        url = f"{self._base}/{path}"
        async with self._session.get(url, headers=await self._headers()) as resp:
            resp.raise_for_status()
            doc = await resp.json()
        return parse_fields(doc)

    async def list_collection(self, path: str) -> list[dict]:
        """List all documents in a collection; returns list of parsed dicts with 'id'."""
        url = f"{self._base}/{path}"
        results: list[dict] = []
        page_token: str | None = None

        while True:
            params = {}
            if page_token:
                params["pageToken"] = page_token
            async with self._session.get(url, headers=await self._headers(), params=params) as resp:
                resp.raise_for_status()
                body = await resp.json()

            for doc in body.get("documents", []):
                item = parse_fields(doc)
                item["_id"] = doc["name"].split("/")[-1]
                results.append(item)

            page_token = body.get("nextPageToken")
            if not page_token:
                break

        return results

    async def patch_document(self, path: str, data: dict, update_mask_fields: list[str]) -> None:
        """Update specific fields of a document."""
        url = f"{self._base}/{path}"
        params = [("updateMask.fieldPaths", f) for f in update_mask_fields]
        payload = {"fields": to_fields(data)}
        async with self._session.patch(
            url, headers=await self._headers(), params=params, json=payload
        ) as resp:
            resp.raise_for_status()

    async def create_document(self, collection_path: str, data: dict) -> str:
        """Create a document with auto-generated ID; returns the new document ID."""
        url = f"{self._base}/{collection_path}"
        payload = {"fields": to_fields(data)}
        async with self._session.post(url, headers=await self._headers(), json=payload) as resp:
            resp.raise_for_status()
            doc = await resp.json()
        return doc["name"].split("/")[-1]
