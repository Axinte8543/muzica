from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from decouple import config


class LastFMAPIError(RuntimeError):
    pass


@dataclass
class LastFMConfig:
    api_key: str


class LastFMClient:
    """Minimal Last.fm client.

    Used for:
    - similar artists (artist.getsimilar)

    Notes:
    - Rate limits are not super strict, but we still throttle lightly.
    """

    def __init__(self) -> None:
        api_key = config("LASTFM_API_KEY", default="").strip()
        self._cfg = LastFMConfig(api_key=api_key)
        self._last_request_at: float | None = None

        if not self._cfg.api_key:
            raise LastFMAPIError(
                "Missing LASTFM_API_KEY. Set it in environment or backend/.env"
            )

    def _sleep_if_needed(self) -> None:
        if self._last_request_at is None:
            return
        dt = time.time() - self._last_request_at
        if dt < 0.25:
            time.sleep(0.25 - dt)

    def request(self, *, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._sleep_if_needed()
        url = "https://ws.audioscrobbler.com/2.0/"
        p = {
            **params,
            "api_key": self._cfg.api_key,
            "format": "json",
        }

        res = requests.request(method.upper(), url, params=p, timeout=30)
        self._last_request_at = time.time()

        if res.status_code < 200 or res.status_code >= 300:
            raise LastFMAPIError(f"Last.fm error: {res.status_code} {res.text}")

        data = res.json()
        if not isinstance(data, dict):
            raise LastFMAPIError("Unexpected Last.fm response shape")

        if "error" in data:
            raise LastFMAPIError(f"Last.fm error: {data.get('message')}")

        return data

    def get_similar_artists(self, *, artist_name: str, limit: int = 10) -> list[dict[str, Any]]:
        name = str(artist_name or "").strip()
        if not name:
            return []

        payload = self.request(
            method="GET",
            params={
                "method": "artist.getsimilar",
                "artist": name,
                "limit": int(limit),
                "autocorrect": 1,
            },
        )

        similar = ((payload.get("similarartists") or {}).get("artist")) or []
        if isinstance(similar, dict):
            similar = [similar]
        if not isinstance(similar, list):
            return []

        result: list[dict[str, Any]] = []
        for a in similar:
            if not isinstance(a, dict):
                continue
            result.append(a)
        return result
