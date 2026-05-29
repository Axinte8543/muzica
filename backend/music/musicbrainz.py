from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from decouple import config


class MusicBrainzAPIError(RuntimeError):
    pass


@dataclass
class MBConfig:
    app_name: str
    contact_email: str

    @property
    def user_agent(self) -> str:
        # MusicBrainz requires a descriptive UA including contact.
        # https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
        email = self.contact_email.strip() if self.contact_email else ""
        if email:
            return f"{self.app_name} ( {email} )"
        return f"{self.app_name}"


class MusicBrainzClient:
    """Minimal MusicBrainz WS/2 client.

    - No OAuth required.
    - Respect rate limiting (1 req/sec is the public guideline).
    """

    def __init__(self) -> None:
        self._cfg = MBConfig(
            app_name=config("MUSICBRAINZ_APP_NAME", default="licenta-muzica"),
            contact_email=config("MUSICBRAINZ_CONTACT_EMAIL", default=""),
        )
        self._last_request_at: float | None = None

    def _sleep_if_needed(self) -> None:
        # Aim for <= 1 request / second.
        if self._last_request_at is None:
            return
        dt = time.time() - self._last_request_at
        if dt < 1.0:
            time.sleep(1.0 - dt)

    def request(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        url = f"https://musicbrainz.org/ws/2{path}"
        p = {**params, "fmt": "json"}

        # MusicBrainz can temporarily reply with 503/5xx. Retry with a small backoff.
        transient = {429, 500, 502, 503, 504}
        max_attempts = 5
        last_status: int | None = None
        last_text: str = ""

        for attempt in range(1, max_attempts + 1):
            self._sleep_if_needed()
            res = requests.get(
                url,
                params=p,
                headers={"User-Agent": self._cfg.user_agent},
                timeout=30,
            )
            self._last_request_at = time.time()

            last_status = int(res.status_code)
            last_text = res.text

            if res.status_code in transient and attempt < max_attempts:
                retry_after = res.headers.get("Retry-After")
                wait_s = 0
                if retry_after is not None:
                    try:
                        wait_s = int(retry_after)
                    except ValueError:
                        wait_s = 0

                if wait_s <= 0:
                    # Exponential-ish backoff capped to 10s.
                    wait_s = min(2 * attempt, 10)

                time.sleep(max(1, wait_s))
                continue

            if res.status_code < 200 or res.status_code >= 300:
                raise MusicBrainzAPIError(f"MusicBrainz error: {res.status_code} {res.text}")

            data = res.json()
            if not isinstance(data, dict):
                raise MusicBrainzAPIError("Unexpected MusicBrainz response shape")
            return data

        raise MusicBrainzAPIError(
            f"MusicBrainz transient error after retries: {last_status} {last_text}"
        )

    def search_artist(self, *, name: str, query: str | None = None, limit: int = 5, offset: int = 0) -> dict[str, Any]:
        q = query.strip() if query else f"artist:{name}".strip()
        return self.request(
            "/artist/",
            params={
                "query": q,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def get_artist(self, *, artist_mbid: str) -> dict[str, Any]:
        """Fetch a single artist by MBID.

        This avoids relying on search query syntax when the MBID is already known.
        """
        mbid = str(artist_mbid or "").strip()
        if not mbid:
            raise MusicBrainzAPIError("Missing artist_mbid")
        return self.request(
            f"/artist/{mbid}",
            params={},
        )

    def artist_release_groups(self, *, artist_mbid: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return self.request(
            "/release-group",
            params={
                "artist": artist_mbid,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def releases_for_release_group(self, *, release_group_mbid: str, limit: int = 25, offset: int = 0) -> dict[str, Any]:
        return self.request(
            "/release/",
            params={
                "release-group": release_group_mbid,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def release_with_recordings(self, *, release_mbid: str) -> dict[str, Any]:
        return self.request(
            f"/release/{release_mbid}",
            params={
                "inc": "recordings+artist-credits",
            },
        )
