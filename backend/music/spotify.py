from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import requests
from decouple import config


class SpotifyAuthError(RuntimeError):
    pass


class SpotifyAPIError(RuntimeError):
    pass


class SpotifyRateLimitError(SpotifyAPIError):
    def __init__(self, *, retry_after_s: int, message: str):
        super().__init__(message)
        self.retry_after_s = int(retry_after_s)


@dataclass
class SpotifyToken:
    access_token: str
    token_type: str
    expires_at: float

    def is_expired(self) -> bool:
        # Safety margin.
        return time.time() >= (self.expires_at - 30)


class SpotifyClient:
    """Tiny Spotify Web API client using Client Credentials flow.

    Notes:
    - This is suitable for metadata import jobs.
    - It does NOT act on behalf of a Spotify user.
    """

    def __init__(self) -> None:
        self._client_id = config("SPOTIFY_CLIENT_ID", default="").strip()
        self._client_secret = config("SPOTIFY_CLIENT_SECRET", default="").strip()
        self._token: SpotifyToken | None = None

        # Tuning knobs for long-running import jobs.
        # - verbose: when True, prints rate-limit waits to stderr.
        # - max_rate_limit_wait_s: if a 429 asks to wait longer than this, raise
        #   SpotifyRateLimitError instead of sleeping.
        self.verbose: bool = False
        self.max_rate_limit_wait_s: int = 3600

        if not self._client_id or not self._client_secret:
            raise SpotifyAuthError(
                "Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET. "
                "Set them in environment or backend/.env"
            )

    def _get_token(self) -> SpotifyToken:
        if self._token and not self._token.is_expired():
            return self._token

        creds = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        auth_header = base64.b64encode(creds).decode("utf-8")

        res = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth_header}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if res.status_code != 200:
            raise SpotifyAuthError(f"Spotify token error: {res.status_code} {res.text}")

        payload = res.json()
        access_token = payload.get("access_token")
        token_type = payload.get("token_type") or "Bearer"
        expires_in = int(payload.get("expires_in") or 3600)

        if not access_token:
            raise SpotifyAuthError("Spotify token response missing access_token")

        self._token = SpotifyToken(
            access_token=str(access_token),
            token_type=str(token_type),
            expires_at=time.time() + expires_in,
        )
        return self._token

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self._get_token()
        url = f"https://api.spotify.com/v1{path}"

        # Backfill/import jobs can run for a long time and may hit rate limits.
        # Keep a higher retry budget to allow the caller to make progress.
        max_attempts = 10
        last_error: SpotifyAPIError | None = None
        for attempt in range(1, max_attempts + 1):
            res = requests.request(
                method.upper(),
                url,
                headers={"Authorization": f"{token.token_type} {token.access_token}"},
                params=params or None,
                timeout=30,
            )

            if res.status_code == 429:
                retry_after = res.headers.get("Retry-After")
                try:
                    raw = int(retry_after) if retry_after is not None else 1
                except ValueError:
                    raw = 1
                # Spotify can return large Retry-After values (minutes). Respect it.
                raw = max(1, raw)

                wait_s = raw
                # Cap to 24h to avoid pathological waits while still allowing
                # legitimate long Retry-After windows.
                wait_s_capped = min(wait_s, 24 * 3600)

                max_wait = int(getattr(self, "max_rate_limit_wait_s", 3600) or 0)
                if max_wait > 0 and wait_s_capped > max_wait:
                    raise SpotifyRateLimitError(
                        retry_after_s=wait_s_capped,
                        message=(
                            f"Spotify rate limit (429). Retry-After={retry_after} (raw_s={raw}) "
                            f"exceeds max_wait_s={max_wait} (effective_wait_s={wait_s_capped})"
                        ),
                    )

                if getattr(self, "verbose", False):
                    import sys

                    sys.stderr.write(
                        f"[spotify] 429 rate limit on {path}. Retry-After={retry_after} (raw_s={raw}); "
                        f"sleeping {wait_s_capped}s (attempt {attempt}/{max_attempts})\n"
                    )
                    sys.stderr.flush()

                time.sleep(wait_s_capped)
                last_error = SpotifyAPIError(f"Spotify rate limit (429). Retry-After={retry_after}")
                continue

            if 500 <= res.status_code <= 599:
                # transient
                time.sleep(min(2 * attempt, 10))
                last_error = SpotifyAPIError(f"Spotify API server error: {res.status_code} {res.text}")
                continue

            if res.status_code < 200 or res.status_code >= 300:
                raise SpotifyAPIError(f"Spotify API error: {res.status_code} {res.text}")

            data = res.json()
            if not isinstance(data, dict):
                raise SpotifyAPIError("Unexpected Spotify response shape")
            return data

        raise last_error or SpotifyAPIError("Spotify request failed after retries")

    def get_playlist_tracks(self, playlist_id: str, *, market: str = "RO", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/playlists/{playlist_id}/tracks",
            params={
                "market": market,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        return self.request("GET", f"/artists/{artist_id}")

    def get_album(self, album_id: str, *, market: str = "RO") -> dict[str, Any]:
        return self.request("GET", f"/albums/{album_id}", params={"market": market})

    def get_artist_albums(
        self,
        artist_id: str,
        *,
        market: str = "RO",
        include_groups: str = "album,single",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        # NOTE: In practice, this endpoint may reject large limits with
        # `400 Invalid limit` depending on API behavior. We clamp to a safe
        # upper bound observed to work reliably.
        safe_limit = max(1, min(int(limit), 5))
        return self.request(
            "GET",
            f"/artists/{artist_id}/albums",
            params={
                "market": market,
                "include_groups": include_groups,
                "limit": int(safe_limit),
                "offset": int(offset),
            },
        )

    def get_album_tracks(
        self,
        album_id: str,
        *,
        market: str = "RO",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/albums/{album_id}/tracks",
            params={
                "market": market,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def get_tracks(self, track_ids: list[str], *, market: str = "RO") -> dict[str, Any]:
        # Spotify: up to 50 ids
        ids = [str(t).strip() for t in track_ids if str(t).strip()]
        if not ids:
            return {"tracks": []}
        return self.request(
            "GET",
            "/tracks",
            params={
                "market": market,
                "ids": ",".join(ids[:50]),
            },
        )

    def search(self, *, q: str, types: list[str], market: str = "RO", limit: int = 10, offset: int = 0) -> dict[str, Any]:
        """Search Spotify catalog.

        types: subset of ["artist", "album", "track"].
        """
        type_param = ",".join([t for t in types if str(t).strip()])
        if not type_param:
            raise SpotifyAPIError("Spotify search requires at least one type")
        return self.request(
            "GET",
            "/search",
            params={
                "q": str(q or "").strip(),
                "type": type_param,
                "market": market,
                "limit": int(limit),
                "offset": int(offset),
            },
        )

    def search_artist(self, *, name: str, market: str = "RO", limit: int = 5) -> list[dict[str, Any]]:
        # NOTE: Spotify's query parser can be surprisingly strict with fielded
        # queries like `artist:...` when names include apostrophes or other
        # punctuation (e.g. "Carla's Dreams"). Using a plain query with
        # type=artist is more robust.
        q = str(name or "").strip()
        if not q:
            return []
        data = self.search(q=q, types=["artist"], market=market, limit=limit)
        items = ((data.get("artists") or {}).get("items")) or []
        return items if isinstance(items, list) else []

    def search_album(self, *, album_title: str, artist_name: str, market: str = "RO", limit: int = 5) -> list[dict[str, Any]]:
        title = str(album_title or "").strip()
        artist = str(artist_name or "").strip()
        q = f"album:{title} artist:{artist}".strip()
        data = self.search(q=q, types=["album"], market=market, limit=limit)
        items = ((data.get("albums") or {}).get("items")) or []
        if isinstance(items, list) and items:
            return items

        # Fallback to a plain query which is more tolerant of punctuation.
        q2 = " ".join([p for p in (title, artist) if p]).strip()
        if not q2:
            return []
        data2 = self.search(q=q2, types=["album"], market=market, limit=limit)
        items2 = ((data2.get("albums") or {}).get("items")) or []
        return items2 if isinstance(items2, list) else []

    def search_track(self, *, track_title: str, artist_name: str, market: str = "RO", limit: int = 5) -> list[dict[str, Any]]:
        title = str(track_title or "").strip()
        artist = str(artist_name or "").strip()
        q = f"track:{title} artist:{artist}".strip()
        data = self.search(q=q, types=["track"], market=market, limit=limit)
        items = ((data.get("tracks") or {}).get("items")) or []
        if isinstance(items, list) and items:
            return items

        q2 = " ".join([p for p in (title, artist) if p]).strip()
        if not q2:
            return []
        data2 = self.search(q=q2, types=["track"], market=market, limit=limit)
        items2 = ((data2.get("tracks") or {}).get("items")) or []
        return items2 if isinstance(items2, list) else []
