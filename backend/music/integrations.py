from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from decouple import config

from .lastfm import LastFMClient, LastFMAPIError
from .musicbrainz import MusicBrainzClient, MusicBrainzAPIError
from .spotify import SpotifyClient, SpotifyAPIError, SpotifyAuthError, SpotifyRateLimitError


class CoverArtArchiveError(RuntimeError):
    pass


@dataclass
class IntegrationClients:
    musicbrainz: MusicBrainzClient | None = None
    spotify: SpotifyClient | None = None
    lastfm: LastFMClient | None = None


class CoverArtArchiveClient:
    """Minimal Cover Art Archive client."""

    def __init__(self, *, user_agent: str = "licenta-muzica") -> None:
        self._ua = user_agent

    def get_release_group_cover_url(self, *, release_group_mbid: str) -> str:
        mbid = str(release_group_mbid or "").strip()
        if not mbid:
            return ""

        res = requests.get(
            f"https://coverartarchive.org/release-group/{mbid}",
            headers={"User-Agent": self._ua},
            timeout=30,
        )
        if res.status_code == 404:
            return ""
        if res.status_code < 200 or res.status_code >= 300:
            raise CoverArtArchiveError(f"Cover Art Archive error: {res.status_code} {res.text}")

        data = res.json()
        if not isinstance(data, dict):
            raise CoverArtArchiveError("Unexpected Cover Art Archive response shape")

        images = data.get("images") or []
        if not isinstance(images, list) or not images:
            return ""

        def score(img: dict[str, Any]) -> tuple[int, int]:
            front = 1 if img.get("front") is True else 0
            approved = 1 if img.get("approved") is True else 0
            return (front, approved)

        imgs = [i for i in images if isinstance(i, dict)]
        if not imgs:
            return ""
        imgs.sort(key=score, reverse=True)
        best = imgs[0]

        thumbs = best.get("thumbnails")
        if isinstance(thumbs, dict):
            for key in ("large", "250", "500"):
                value = str(thumbs.get(key) or "").strip()
                if value:
                    return value

        return str(best.get("image") or "").strip()


@dataclass
class ExternalLookupResult:
    source: str
    payload: dict[str, Any]


class MusicExternalIntegrationService:
    """Single orchestration layer for third-party music integrations.

    The goal is to keep all vendor-specific clients behind one stable surface.
    """

    def __init__(self) -> None:
        self._clients = IntegrationClients()
        self._caa = CoverArtArchiveClient(user_agent=self.user_agent)

    @property
    def user_agent(self) -> str:
        app_name = config("MUSICBRAINZ_APP_NAME", default="licenta-muzica").strip() or "licenta-muzica"
        contact_email = config("MUSICBRAINZ_CONTACT_EMAIL", default="").strip()
        return f"{app_name} ({contact_email})" if contact_email else app_name

    @property
    def musicbrainz(self) -> MusicBrainzClient:
        if self._clients.musicbrainz is None:
            self._clients.musicbrainz = MusicBrainzClient()
        return self._clients.musicbrainz

    @property
    def spotify(self) -> SpotifyClient:
        if self._clients.spotify is None:
            self._clients.spotify = SpotifyClient()
        return self._clients.spotify

    @property
    def lastfm(self) -> LastFMClient:
        if self._clients.lastfm is None:
            self._clients.lastfm = LastFMClient()
        return self._clients.lastfm

    @property
    def cover_art_archive(self) -> CoverArtArchiveClient:
        return self._caa

    def resolve_artist_cover(self, *, artist_name: str, spotify_id: str | None = None, market: str = "RO") -> ExternalLookupResult | None:
        if spotify_id:
            payload = self.spotify.get_artist(spotify_id)
            return ExternalLookupResult(source="spotify", payload=payload)

        candidates = self.spotify.search_artist(name=artist_name, market=market, limit=3)
        if candidates:
            return ExternalLookupResult(source="spotify-search", payload=candidates[0])
        return None

    def resolve_album_cover(
        self,
        *,
        album_title: str,
        artist_name: str,
        spotify_id: str | None = None,
        musicbrainz_id: str | None = None,
        market: str = "RO",
    ) -> ExternalLookupResult | None:
        if spotify_id:
            payload = self.spotify.get_album(spotify_id, market=market)
            return ExternalLookupResult(source="spotify", payload=payload)

        candidates = self.spotify.search_album(
            album_title=album_title,
            artist_name=artist_name,
            market=market,
            limit=3,
        )
        if candidates:
            return ExternalLookupResult(source="spotify-search", payload=candidates[0])

        if musicbrainz_id:
            cover_url = self.cover_art_archive.get_release_group_cover_url(release_group_mbid=musicbrainz_id)
            if cover_url:
                return ExternalLookupResult(source="cover-art-archive", payload={"cover_url": cover_url})

        return None


def safe_image_url(payload: Any) -> str:
    images = payload.get("images") if isinstance(payload, dict) else None
    if not isinstance(images, list) or not images:
        return ""
    first = images[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("url") or "").strip()


__all__ = [
    "CoverArtArchiveClient",
    "CoverArtArchiveError",
    "ExternalLookupResult",
    "LastFMAPIError",
    "MusicBrainzAPIError",
    "MusicExternalIntegrationService",
    "SpotifyAPIError",
    "SpotifyAuthError",
    "SpotifyClient",
    "SpotifyRateLimitError",
    "safe_image_url",
]