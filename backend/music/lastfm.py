from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError
import json

from decouple import config


class LastFMAPIError(RuntimeError):
    pass


@dataclass
class LastFMConfig:
    api_key: str


class LastFMClient:
\
\
\
\
\
\
\
       

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

        if method.upper() != "GET":
            raise LastFMAPIError("Last.fm client only supports GET requests")

        full_url = f"{url}?{parse.urlencode(p)}"
        try:
            with request.urlopen(full_url, timeout=30) as res:
                self._last_request_at = time.time()
                status = getattr(res, "status", 200)
                body = res.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            self._last_request_at = time.time()
            body = exc.read().decode("utf-8", errors="replace")
            raise LastFMAPIError(f"Last.fm error: {exc.code} {body}") from exc
        except URLError as exc:
            self._last_request_at = time.time()
            raise LastFMAPIError(f"Last.fm request failed: {exc.reason}") from exc

        if status < 200 or status >= 300:
            raise LastFMAPIError(f"Last.fm error: {status} {body}")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LastFMAPIError("Unexpected Last.fm JSON response") from exc
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

    def get_artist_info(self, *, artist_name: str = "", artist_mbid: str = "", lang: str = "en") -> dict[str, Any]:
        name = str(artist_name or "").strip()
        mbid = str(artist_mbid or "").strip()
        if not name and not mbid:
            return {}

        attempts: list[dict[str, Any]] = []
        if mbid:
            attempts.append({"mbid": mbid})
        if name:
            attempts.append({"artist": name})

        last_error: LastFMAPIError | None = None
        for artist_params in attempts:
            params: dict[str, Any] = {
                "method": "artist.getinfo",
                "autocorrect": 1,
                **artist_params,
            }
            if str(lang or "").strip():
                params["lang"] = str(lang).strip()

            try:
                payload = self.request(method="GET", params=params)
            except LastFMAPIError as exc:
                last_error = exc
                continue

            artist = payload.get("artist")
            if isinstance(artist, dict):
                return artist

        if last_error is not None:
            raise last_error
        return {}

    def get_top_albums(self, *, artist_name: str = "", artist_mbid: str = "", limit: int = 10) -> list[dict[str, Any]]:
        name = str(artist_name or "").strip()
        mbid = str(artist_mbid or "").strip()
        if not name and not mbid:
            return []

        artist_params = {"mbid": mbid} if mbid else {"artist": name}
        payload = self.request(
            method="GET",
            params={
                "method": "artist.gettopalbums",
                "limit": int(limit),
                "autocorrect": 1,
                **artist_params,
            },
        )

        albums = ((payload.get("topalbums") or {}).get("album")) or []
        if isinstance(albums, dict):
            albums = [albums]
        if not isinstance(albums, list):
            return []
        return [album for album in albums if isinstance(album, dict)]

    def get_top_tracks(self, *, artist_name: str = "", artist_mbid: str = "", limit: int = 20) -> list[dict[str, Any]]:
        name = str(artist_name or "").strip()
        mbid = str(artist_mbid or "").strip()
        if not name and not mbid:
            return []

        artist_params = {"mbid": mbid} if mbid else {"artist": name}
        payload = self.request(
            method="GET",
            params={
                "method": "artist.gettoptracks",
                "limit": int(limit),
                "autocorrect": 1,
                **artist_params,
            },
        )

        tracks = ((payload.get("toptracks") or {}).get("track")) or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not isinstance(tracks, list):
            return []
        return [track for track in tracks if isinstance(track, dict)]

    def get_album_info(self, *, artist_name: str, album_title: str) -> dict[str, Any]:
        artist = str(artist_name or "").strip()
        album = str(album_title or "").strip()
        if not artist or not album:
            return {}

        payload = self.request(
            method="GET",
            params={
                "method": "album.getinfo",
                "artist": artist,
                "album": album,
                "autocorrect": 1,
            },
        )
        data = payload.get("album")
        return data if isinstance(data, dict) else {}
