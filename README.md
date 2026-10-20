# roMusic

This project proposes the development of a web platform dedicated exclusively to Romanian music, allowing users to discover, evaluate, and discuss albums, artists and songs from the discographies of Romanian artists. The platform functions as an equivalent of Letterboxd for films, but adapted to the music domain, offering advanced features for rating, commenting, creating lists and social interaction.

Users can assign ratings, write reviews, follow artists, create personalized lists and interact with other users who share similar musical interests. The content is organized by years, decades, musical genres and popularity, while data about artists and albums is validated through an administrative moderation system.

## Features

### Music Discovery
- Browse artists, albums, and songs.
- Explore artist discographies, similar artists, and top songs.
- Discover new releases, highly rated albums, and random artists or albums.
- Search the music catalog and filter albums.

### Ratings and Reviews
- Rate artists, albums, and songs.
- Write album reviews and discuss music through comments.
- React to reviews and comments.
- Save favorite albums and songs.

### Personal Music Library
- Record album listens and view listening history.
- Maintain a Want to Listen collection.
- Create and organize album lists.
- Share public lists and collaborate with other users.

### Personalized Recommendations
- Discover albums based on ratings, favorites, listening activity, and followed artists.
- Explore recommendations influenced by users with similar tastes.
- Find music through friends' ratings and reviews.

### Community
- Add friends and explore community activity feeds.
- Follow artists and visit user profiles.
- Exchange direct messages and receive notifications.
- Discover users with similar music preferences.

### Statistics and Gamification
- Explore personal listening statistics and weekly recaps.
- Track listening streaks and complete weekly challenges.
- Earn badges, achievements, and experience points.

### Account Management
- Email verification and password recovery.
- Two-factor authentication and passkey support.
- Active session management and privacy settings.
- Personal data import and export.

## Technology Stack

| Area | Technologies |
|------|--------------|
| Frontend | React, Vite, React Router |
| Data Fetching | Axios, TanStack Query |
| Charts | Recharts |
| Backend | Python, Django, Django REST Framework |
| Authentication | JWT, TOTP, WebAuthn |
| Database | SQLite for local development; PostgreSQL support |
| Caching and Background Tasks | Redis, Celery |
| Deployment | Docker Compose, Gunicorn |
| Testing | Django tests, Vitest, Playwright, axe-core, Locust |

## Music Data Integrations

The backend includes integrations with MusicBrainz, Spotify, and Last.fm
to import and enrich music metadata, including artist information,
discographies, track listings, and artwork.

Integration availability depends on API credentials and service restrictions.

## Recommendation System

roMusic combines several recommendation signals:

- Explicit preferences, such as ratings and favorites.
- Listening history and other music interactions.
- Followed artists and album metadata.
- Preferences from users with similar music tastes.
- Friends' ratings and reviews.
- Item-based collaborative filtering using album ratings.

## Project Structure

- `frontend/` — React interface, routing, API integration, and frontend tests.
- `backend/music/` — Music catalog, discovery endpoints, and metadata integrations.
- `backend/interactions/` — Ratings, reviews, lists, recommendations, and social features.
- `backend/users/` — Authentication and account management.
- `backend/config/` — Django configuration.
- `docker-compose.yml` — Backend, Redis, and Celery services.
