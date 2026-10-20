from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

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
                        
        return time.time() >= (self.expires_at - 30)


class SpotifyClient:
\
\
\
\
\
       

    def __init__(self) -> None:
        self._client_id = config("SPOTIFY_CLIENT_ID", default="").strip()
        self._client_secret = config("SPOTIFY_CLIENT_SECRET", default="").strip()
        self._token: SpotifyToken | None = None

                                                    
                                                                  
                                                                                
                                                      
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

        body = parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        req = request.Request(
            "https://accounts.spotify.com/api/token",
            data=body,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as res:
                status = getattr(res, "status", 200)
                response_body = res.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise SpotifyAuthError(f"Spotify token error: {exc.code} {response_body}") from exc
        except URLError as exc:
            raise SpotifyAuthError(f"Spotify token request failed: {exc.reason}") from exc

        if status != 200:
            raise SpotifyAuthError(f"Spotify token error: {status} {response_body}")

        payload = json.loads(response_body)
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

                                                                               
                                                                          
        max_attempts = 10
        last_error: SpotifyAPIError | None = None
        for attempt in range(1, max_attempts + 1):
            full_url = url
            if params:
                full_url = f"{url}?{parse.urlencode(params)}"
            req = request.Request(
                full_url,
                headers={"Authorization": f"{token.token_type} {token.access_token}"},
                method=method.upper(),
            )
            try:
                with request.urlopen(req, timeout=30) as res:
                    status = getattr(res, "status", 200)
                    headers = res.headers
                    response_body = res.read().decode("utf-8", errors="replace")
            except HTTPError as exc:
                status = int(exc.code)
                headers = exc.headers
                response_body = exc.read().decode("utf-8", errors="replace")
            except URLError as exc:
                time.sleep(min(2 * attempt, 10))
                last_error = SpotifyAPIError(f"Spotify request failed: {exc.reason}")
                continue

            if status == 429:
                retry_after = headers.get("Retry-After")
                try:
                    raw = int(retry_after) if retry_after is not None else 1
                except ValueError:
                    raw = 1
                                                                                    
                raw = max(1, raw)

                wait_s = raw
                                                                             
                                                      
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

            if 500 <= status <= 599:
                           
                time.sleep(min(2 * attempt, 10))
                last_error = SpotifyAPIError(f"Spotify API server error: {status} {response_body}")
                continue

            if status < 200 or status >= 300:
                raise SpotifyAPIError(f"Spotify API error: {status} {response_body}")

            data = json.loads(response_body)
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
