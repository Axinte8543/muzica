from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

from decouple import config


class MusicBrainzAPIError(RuntimeError):
    pass


@dataclass
class MBConfig:
    app_name: str
    contact_email: str

    @property
    def user_agent(self) -> str:
                                                                  
                                                                   
        email = self.contact_email.strip() if self.contact_email else ""
        if email:
            return f"{self.app_name} ( {email} )"
        return f"{self.app_name}"


class MusicBrainzClient:
\
\
\
\
       

    def __init__(self) -> None:
        self._cfg = MBConfig(
            app_name=config("MUSICBRAINZ_APP_NAME", default="licenta-muzica"),
            contact_email=config("MUSICBRAINZ_CONTACT_EMAIL", default=""),
        )
        self._last_request_at: float | None = None

    def _sleep_if_needed(self) -> None:
                                        
        if self._last_request_at is None:
            return
        dt = time.time() - self._last_request_at
        if dt < 1.0:
            time.sleep(1.0 - dt)

    def request(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        url = f"https://musicbrainz.org/ws/2{path}"
        p = {**params, "fmt": "json"}

                                                                                     
        transient = {429, 500, 502, 503, 504}
        max_attempts = 5
        last_status: int | None = None
        last_text: str = ""

        for attempt in range(1, max_attempts + 1):
            self._sleep_if_needed()
            full_url = f"{url}?{parse.urlencode(p)}"
            req = request.Request(
                full_url,
                headers={"User-Agent": self._cfg.user_agent},
                method="GET",
            )
            try:
                with request.urlopen(req, timeout=60) as res:
                    status = int(getattr(res, "status", 200))
                    headers = res.headers
                    text = res.read().decode("utf-8", errors="replace")
            except TimeoutError as exc:
                self._last_request_at = time.time()
                last_status = 0
                last_text = str(exc)
                if attempt < max_attempts:
                    time.sleep(min(2 * attempt, 10))
                    continue
                raise MusicBrainzAPIError(f"MusicBrainz request timed out after retries: {exc}")
            except HTTPError as exc:
                self._last_request_at = time.time()
                status = int(exc.code)
                headers = exc.headers
                text = exc.read().decode("utf-8", errors="replace")
            except URLError as exc:
                self._last_request_at = time.time()
                last_status = 0
                last_text = str(exc)
                if attempt < max_attempts:
                    time.sleep(min(2 * attempt, 10))
                    continue
                raise MusicBrainzAPIError(f"MusicBrainz request failed after retries: {exc}")

            self._last_request_at = time.time()

            last_status = int(status)
            last_text = text

            if status in transient and attempt < max_attempts:
                retry_after = headers.get("Retry-After")
                wait_s = 0
                if retry_after is not None:
                    try:
                        wait_s = int(retry_after)
                    except ValueError:
                        wait_s = 0

                if wait_s <= 0:
                                                            
                    wait_s = min(2 * attempt, 10)

                time.sleep(max(1, wait_s))
                continue

            if status < 200 or status >= 300:
                raise MusicBrainzAPIError(f"MusicBrainz error: {status} {text}")

            data = json.loads(text)
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

    def get_artist(self, *, artist_mbid: str, inc: str = "") -> dict[str, Any]:
           
        mbid = str(artist_mbid or "").strip()
        if not mbid:
            raise MusicBrainzAPIError("Missing artist_mbid")
        params: dict[str, Any] = {}
        include = str(inc or "").strip()
        if include:
            params["inc"] = include
        return self.request(
            f"/artist/{mbid}",
            params=params,
        )

    def get_release_group(self, *, release_group_mbid: str) -> dict[str, Any]:
        mbid = str(release_group_mbid or "").strip()
        if not mbid:
            raise MusicBrainzAPIError("Missing release_group_mbid")
        return self.request(
            f"/release-group/{mbid}",
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
